import os
import time
import shutil
import subprocess
import logging
from datetime import datetime
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from utils import load_config, get_cost_estimate
from prompts import SYSTEM_PROMPT

logger = logging.getLogger("AIVoice")

class AudioProcessor:
    def __init__(self, config):
        self.config = config
        self.setup_gemini()
        self.processing_files = set()

    def setup_gemini(self):
        api_key = os.getenv("GEMINI_API_KEY") or self.config['gemini']['api_key']
        if not api_key or api_key == "YOUR_KEY_HERE":
             logger.warning("Gemini API Key not found in env or config. Please set it.")
        genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel(
            model_name=self.config['gemini']['model'],
            system_instruction=SYSTEM_PROMPT
        )

    def process_file(self, filepath):
        if filepath in self.processing_files:
            logger.info(f"Skipping {filepath} - already processing.")
            return
        
        self.processing_files.add(filepath)
        
        # Wait for file to be ready (simple debounce)
        if not self.wait_for_file(filepath):
            logger.error(f"File {filepath} not found or not ready after waiting.")
            self.processing_files.remove(filepath)
            return

        start_time = time.time()
        filename = os.path.basename(filepath)
        logger.info(f"Starting processing for: {filename}")

        try:
            # 1. Compress Audio
            compressed_path = self.compress_audio(filepath)
            
            # 2. Upload to Gemini
            gemini_file = self.upload_to_gemini(compressed_path)
            
            # 3. Generate Content
            response = self.generate_content(gemini_file)
            
            # 4. Save Results
            self.save_results(filepath, compressed_path, response, start_time)
            
            # 5. Cleanup
            self.cleanup(filepath, compressed_path, gemini_file)
            
            logger.info(f"Successfully processed: {filename}")

        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}")
            self.handle_failure(filepath)
        finally:
            if filepath in self.processing_files:
                self.processing_files.remove(filepath)

    def wait_for_file(self, filepath, timeout=10):
        """Waits for file to exist and size to stabilize."""
        start = time.time()
        last_size = -1
        
        while time.time() - start < timeout:
            if os.path.exists(filepath):
                current_size = os.path.getsize(filepath)
                if current_size == last_size and current_size > 0:
                    return True
                last_size = current_size
            time.sleep(1)
        return False

    def compress_audio(self, input_path):
        logger.info("Compressing audio...")
        filename = os.path.basename(input_path)
        name_without_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(os.path.dirname(input_path), f"{name_without_ext}_compressed.ogg")
        
        bitrate = self.config['audio']['bitrate']
        
        cmd = [
            'ffmpeg', '-y', # Overwrite
            '-i', input_path,
            '-c:a', 'libopus',
            '-b:a', bitrate,
            '-ac', '1', # Mono
            '-ar', '16000', # 16kHz
            '-vn', # No video
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg compression failed: {e}")
            raise

    def upload_to_gemini(self, filepath):
        logger.info("Uploading to Gemini...")
        file = genai.upload_file(filepath, mime_type="audio/ogg")
        
        # Wait for processing
        while file.state.name == "PROCESSING":
            time.sleep(2)
            file = genai.get_file(file.name)
            
        if file.state.name == "FAILED":
            raise ValueError("Gemini file processing failed.")
            
        return file

    def generate_content(self, file):
        logger.info("Generating transcription and summary...")
        # Safety settings to avoid blocking legitimate content
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        response = self.model.generate_content(
            [file, "Transcribe and summarize this audio."],
            safety_settings=safety_settings
        )
        return response

    def save_results(self, original_path, compressed_path, response, start_time):
        logger.info("Saving results...")
        
        # Create directory structure
        now = datetime.now()
        filename = os.path.basename(original_path)
        name_without_ext = os.path.splitext(filename)[0]
        
        # Get file creation time (metadata)
        try:
            creation_time = os.path.getctime(original_path)
            creation_date_str = datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.warning(f"Could not get creation time: {e}")
            creation_date_str = "Unknown"

        timestamp = now.strftime("%H%M%S")
        folder_name = f"{timestamp}-{name_without_ext}"
        
        year = now.strftime("%Y")
        month = now.strftime("%m")
        
        results_dir = self.config['paths']['results']
        target_dir = os.path.join(results_dir, year, month, folder_name)
        os.makedirs(target_dir, exist_ok=True)
        
        # Save compressed audio
        shutil.copy2(compressed_path, os.path.join(target_dir, "compressed.ogg"))
        
        # Process text content
        text_content = response.text
        
        parts = text_content.split("---SPLIT_OUTPUT_HERE---")
        
        raw_transcript = ""
        structured_content = ""
        
        if len(parts) >= 2:
            raw_transcript = parts[0].strip()
            structured_content = parts[1].strip()
        else:
            logger.warning("Could not split response into two parts. Saving all to both files.")
            raw_transcript = text_content
            structured_content = text_content

        # Add metadata to structured content
        meta_header = f"**Original File Date:** {creation_date_str}\n**Processed Date:** {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        structured_content = meta_header + structured_content

        # Save Raw Transcript
        with open(os.path.join(target_dir, "raw_transcript.md"), "w") as f:
            f.write(raw_transcript)

        # Save Structured Content
        with open(os.path.join(target_dir, "structured.md"), "w") as f:
            f.write(structured_content)
            
        # Calculate stats
        end_time = time.time()
        duration = end_time - start_time
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        cost = get_cost_estimate(input_tokens, output_tokens)
        
        log_content = (
            f"Processing Log for {filename}\n"
            f"Original Date: {creation_date_str}\n"
            f"Processed Date: {now.isoformat()}\n"
            f"Duration: {duration:.2f} seconds\n"
            f"Input Tokens: {input_tokens}\n"
            f"Output Tokens: {output_tokens}\n"
            f"Estimated Cost: {cost}\n"
        )
        
        with open(os.path.join(target_dir, "session.log"), "w") as f:
            f.write(log_content)
            
        # Print to console
        print("\n" + "="*30)
        print(f"DONE: {filename}")
        print(f"Original Date: {creation_date_str}")
        print(f"Time: {duration:.2f}s")
        print(f"Tokens: {input_tokens} in / {output_tokens} out")
        print(f"Cost: {cost}")
        print("="*30 + "\n")

    def cleanup(self, original_path, compressed_path, gemini_file):
        # Move original to processed (optional, or delete)
        # For now, let's just delete the compressed temp file
        if os.path.exists(compressed_path):
            os.remove(compressed_path)
            
        # Move original file to 'processed' folder inside input or just delete?
        # Spec says: "Исходный файл перемещается в processed (или удаляется)"
        # Let's create a 'processed' folder in the input directory
        processed_dir = os.path.join(os.path.dirname(original_path), "processed")
        os.makedirs(processed_dir, exist_ok=True)
        shutil.move(original_path, os.path.join(processed_dir, os.path.basename(original_path)))
        
        # Delete from Gemini
        try:
            genai.delete_file(gemini_file.name)
        except Exception as e:
            logger.warning(f"Failed to delete file from Gemini: {e}")

    def handle_failure(self, filepath):
        quarantine_dir = self.config['paths']['quarantine']
        os.makedirs(quarantine_dir, exist_ok=True)
        try:
            shutil.move(filepath, os.path.join(quarantine_dir, os.path.basename(filepath)))
            logger.info(f"Moved {filepath} to quarantine.")
        except Exception as e:
            logger.error(f"Failed to move to quarantine: {e}")
