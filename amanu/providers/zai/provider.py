import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from zhipuai import ZhipuAI
import anthropic

from ...core.providers import TranscriptionProvider, IngestSpecs, RefinementProvider
from ...core.models import JobConfiguration
from ...core.logger import APILogger
from . import ZaiConfig

logger = logging.getLogger("Amanu.Plugin.Zai")

class ZaiProvider(TranscriptionProvider):
    def __init__(self, config: JobConfiguration, provider_config: ZaiConfig):
        super().__init__(config, provider_config)
        self.zai_config = provider_config
        if not self.zai_config or not self.zai_config.api_key:
            raise ValueError("Zai API Key not found in config.")
        self.client = ZhipuAI(api_key=self.zai_config.api_key.get_secret_value())

    @classmethod
    def get_ingest_specs(cls) -> IngestSpecs:
        return IngestSpecs(
            target_format="mp3",
            requires_upload=False,
            upload_target="none"
        )

    def transcribe(self, ingest_result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        job_dir = kwargs.get("job_dir")
        api_logger = APILogger(job_dir) if job_dir else None
        
        local_file_path = ingest_result.get("local_file_path")
        if not local_file_path:
            raise ValueError("No local file path found in Ingest result for Zai.")

        logger.info(f"Transcribing {local_file_path} with Zhipu AI...")

        with open(local_file_path, "rb") as audio_file:
            if api_logger:
                api_logger.log("zai", "audio.transcriptions.create", {"model": self.config.transcribe.model or "glm-4.5-air", "file": str(local_file_path)}, "PENDING")
            
            try:
                response = self.client.audio.transcriptions.create(
                    model=self.config.transcribe.model or "glm-4.5-air",
                    file=audio_file,
                )
                
                if api_logger:
                    api_logger.log("zai", "audio.transcriptions.create", {"model": self.config.transcribe.model or "glm-4.5-air"}, response.model_dump() if hasattr(response, 'model_dump') else str(response))
                    
            except Exception as e:
                if api_logger:
                    api_logger.log("zai", "audio.transcriptions.create", {"model": self.config.transcribe.model or "glm-4.5-air"}, None, error=str(e))
                raise

        full_text = response.text
        segments = []
        if full_text:
            segments.append({
                "speaker_id": "Speaker A",
                "start_time": 0.0,
                "end_time": 0.0,
                "text": full_text,
                "confidence": 1.0
            })

        return {
            "segments": segments,
            "tokens": {"input": 0, "output": 0},
            "cost_usd": 0.0,
            "analysis": {}
        }


class ZaiRefinementProvider(RefinementProvider):
    """Refinement provider for Zhipu AI using Claude-compatible endpoint and native chat API."""

    def __init__(self, config: JobConfiguration, provider_config: ZaiConfig):
        super().__init__(config, provider_config)
        self.zai_config = provider_config
        if not self.zai_config or not self.zai_config.api_key:
            raise ValueError("Zai API Key not found in config.")

        # Initialize ZhipuAI client
        self.zhipu_client = ZhipuAI(api_key=self.zai_config.api_key.get_secret_value())

        # For Claude-compatible endpoint (if base_url is configured)
        base_url = getattr(self.zai_config, 'base_url', None)
        if base_url:
            self.claude_client = anthropic.Anthropic(
                api_key=self.zai_config.api_key.get_secret_value(),
                base_url=base_url
            )
            logger.info("Claude-compatible endpoint available for refinement")
        else:
            self.claude_client = None
            logger.info("Using native ZhipuAI chat API for refinement")

    def _extract_text_from_input(self, input_data: Any, mode: str) -> str:
        """Extract text content from input data based on mode."""
        if mode == "standard":
            # Text mode - input is transcript data
            if isinstance(input_data, dict):
                segments = input_data.get("segments", [])
                if segments:
                    return " ".join([seg.get("text", "") for seg in segments])
                elif "text" in input_data:
                    return input_data["text"]
            return str(input_data)
        elif mode == "direct":
            # Direct mode - input contains ingest result with file info
            if isinstance(input_data, dict):
                file_path = input_data.get("local_file_path", "")
                return f"Audio file for analysis: {file_path}"
            return str(input_data)
        else:
            return str(input_data)

    def _build_refinement_prompt(self, text: str, language: Optional[str] = None, custom_schema: Optional[Dict] = None) -> str:
        """Build the refinement prompt for text analysis including custom fields."""
        language_context = f"Language: {language}" if language else "Language: auto-detected"

        base_prompt = f"""Analyze the following transcribed text and provide a comprehensive summary and analysis.

{language_context}

Please provide the following structured information:
1. A concise summary of the main topics and content
2. Key points and highlights
3. Overall sentiment or tone
4. Important entities mentioned (people, places, organizations)
5. Any action items or decisions mentioned

Text to analyze:
{text}"""

        if custom_schema:
            schema_instructions = "\n\nAdditionally, please extract the following custom fields:\n"
            for field_name, field_desc in custom_schema.items():
                schema_instructions += f"- {field_name}: {field_desc}\n"
            base_prompt += schema_instructions

        base_prompt += """

Please format your response in a clear, structured way that can be easily parsed."""

        return base_prompt

    def refine(self, input_data: Any, mode: str, **kwargs) -> Dict[str, Any]:
        """Refine and analyze transcribed text with custom fields support."""
        language = kwargs.get("language")
        custom_schema = kwargs.get("custom_schema", {})
        job_dir = kwargs.get("job_dir")
        api_logger = APILogger(job_dir) if job_dir else None

        # Extract text content
        text_content = self._extract_text_from_input(input_data, mode)

        if not text_content.strip():
            logger.warning("No text content found for refinement")
            empty_result = {
                "summary": "No content available for analysis.",
                "key_points": [],
                "sentiment": "neutral",
                "entities": [],
                "action_items": []
            }
            # Add empty custom fields
            for field_name in custom_schema.keys():
                empty_result[field_name] = ""

            return {
                "result": empty_result,
                "usage": None
            }

        logger.info(f"Refining {mode} mode content with Zhipu AI...")

        try:
            # Try Claude-compatible endpoint first if available
            if self.claude_client:
                return self._refine_with_claude(text_content, language, custom_schema, api_logger)
            else:
                return self._refine_with_zhipu(text_content, language, custom_schema, api_logger)
        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            # Try the other method as fallback
            # Try the other method as fallback
            try:
                if self.claude_client:
                    logger.info("Falling back to ZhipuAI native API...")
                    return self._refine_with_zhipu(text_content, language, custom_schema, api_logger)
                else:
                    # We tried zhipu (because claude was None), failed.
                    # We cannot try claude because it is None.
                    logger.error("ZhipuAI native API failed and no Claude-compatible endpoint configured.")
                    raise e
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                raise

    def _refine_with_claude(self, text_content: str, language: Optional[str], custom_schema: Dict, api_logger: Optional[APILogger] = None) -> Dict[str, Any]:
        """Use Claude-compatible endpoint for refinement."""
        prompt = self._build_refinement_prompt(text_content, language, custom_schema)
        model = self.config.refine.model or "claude-3-haiku-20240307"

        try:
            if api_logger:
                api_logger.log("zai_claude", "messages.create", {"model": model, "prompt": prompt}, "PENDING")
                
            response = self.claude_client.messages.create(
                model=model,
                max_tokens=3000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            if api_logger:
                api_logger.log("zai_claude", "messages.create", {"model": model}, response.model_dump() if hasattr(response, 'model_dump') else str(response))

            content = response.content[0].text if response.content else ""

            # Parse response into structured format
            result = self._parse_refinement_response(content, custom_schema)

            # Get usage info if available
            usage = getattr(response, 'usage', None)

            return {
                "result": result,
                "usage": usage
            }

        except Exception as e:
            if api_logger:
                api_logger.log("zai_claude", "messages.create", {"model": model}, None, error=str(e))
            logger.error(f"Claude-compatible refinement failed: {e}")
            raise

    def _refine_with_zhipu(self, text_content: str, language: Optional[str], custom_schema: Dict, api_logger: Optional[APILogger] = None) -> Dict[str, Any]:
        """Use Zhipu native API for refinement."""
        prompt = self._build_refinement_prompt(text_content, language, custom_schema)
        model = self.config.refine.model or "glm-4"

        try:
            if api_logger:
                api_logger.log("zai_native", "chat.completions.create", {"model": model, "prompt": prompt}, "PENDING")
                
            response = self.zhipu_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000
            )
            
            if api_logger:
                api_logger.log("zai_native", "chat.completions.create", {"model": model}, response.model_dump() if hasattr(response, 'model_dump') else str(response))

            content = response.choices[0].message.content if response.choices else ""

            # Parse response into structured format
            result = self._parse_refinement_response(content, custom_schema)

            # Get usage info if available
            usage = getattr(response, 'usage', None)

            return {
                "result": result,
                "usage": usage
            }

        except Exception as e:
            if api_logger:
                api_logger.log("zai_native", "chat.completions.create", {"model": model}, None, error=str(e))
            logger.error(f"Zhipu refinement failed: {e}")
            raise

    def _parse_refinement_response(self, content: str, custom_schema: Dict) -> Dict[str, Any]:
        """Parse the LLM response into structured format including custom fields."""
        # Initialize result structure
        result = {
            "summary": "",
            "key_points": [],
            "sentiment": "neutral",
            "entities": [],
            "action_items": []
        }

        # Add custom fields to result
        for field_name in custom_schema.keys():
            result[field_name] = ""

        # Enhanced parsing with better pattern recognition
        lines = content.split('\n')
        current_section = None
        current_list_items = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect section headers with various patterns
            lower_line = line.lower()

            # Summary detection
            if any(keyword in lower_line for keyword in ["summary", "краткий", "резюме", "основное"]):
                current_section = "summary"
                # Check if content follows on same line after colon
                if ":" in line:
                    result["summary"] = line.split(":", 1)[1].strip() + " "
                continue

            # Key points detection
            elif any(keyword in lower_line for keyword in ["key point", "основной пункт", "важный момент", "выделение"]):
                current_section = "key_points"
                continue

            # Sentiment detection
            elif any(keyword in lower_line for keyword in ["sentiment", "тональность", "настроение", "эмоции"]):
                current_section = "sentiment"
                if ":" in line:
                    result["sentiment"] = line.split(":", 1)[1].strip()
                continue

            # Entities detection
            elif any(keyword in lower_line for keyword in ["entit", "сущность", "персонаж", "организация", "место"]):
                current_section = "entities"
                continue

            # Action items detection
            elif any(keyword in lower_line for keyword in ["action", "действие", "задача", "решение", "план"]):
                current_section = "action_items"
                continue

            # Custom fields detection
            custom_field_found = False
            for field_name in custom_schema.keys():
                if field_name.lower() in lower_line:
                    current_section = f"custom_{field_name}"
                    if ":" in line:
                        result[field_name] = line.split(":", 1)[1].strip()
                    custom_field_found = True
                    break

            if custom_field_found:
                continue

            # Process content based on current section
            if current_section == "summary":
                result["summary"] += line + " "

            elif current_section == "key_points":
                if line.startswith(('-', '*', '•', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    # List item
                    clean_item = line.lstrip('-*•0123456789. ').strip()
                    if clean_item:
                        result["key_points"].append(clean_item)
                else:
                    # Continuation of previous point
                    if result["key_points"]:
                        result["key_points"][-1] += " " + line

            elif current_section == "entities":
                if line.startswith(('-', '*', '•', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    clean_item = line.lstrip('-*•0123456789. ').strip()
                    if clean_item:
                        result["entities"].append(clean_item)
                else:
                    # Continuation of previous entity
                    if result["entities"]:
                        result["entities"][-1] += " " + line

            elif current_section == "action_items":
                if line.startswith(('-', '*', '•', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    clean_item = line.lstrip('-*•0123456789. ').strip()
                    if clean_item:
                        result["action_items"].append(clean_item)
                else:
                    # Continuation of previous action item
                    if result["action_items"]:
                        result["action_items"][-1] += " " + line

            elif current_section and current_section.startswith("custom_"):
                field_name = current_section.replace("custom_", "")
                if line.startswith(('-', '*', '•')):
                    # List format for custom fields
                    clean_item = line.lstrip('-*• ').strip()
                    if result[field_name]:
                        result[field_name] += "; " + clean_item
                    else:
                        result[field_name] = clean_item
                else:
                    # Continuation
                    result[field_name] += " " + line

        # Clean up summary
        result["summary"] = result["summary"].strip()

        # If no structured content found, use the whole response as summary
        if not result["summary"] and content.strip():
            result["summary"] = content.strip()

        # Clean up custom fields
        for field_name in custom_schema.keys():
            result[field_name] = result[field_name].strip()

        logger.info(f"Parsed refinement response with {len(result['key_points'])} key points, {len(result['entities'])} entities, {len(result['action_items'])} action items")

        return result
