import os
import time
import shutil
import subprocess
import logging
import json
import uuid
import hashlib
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .utils import load_config, get_cost_estimate
from .prompts import get_system_prompt

logger = logging.getLogger("Amanu")

class AudioHandler(FileSystemEventHandler):
    def __init__(self, scribe):
        self.scribe = scribe

    def on_created(self, event):
        if event.is_directory:
            return
        
        filename = event.src_path
        if filename.lower().endswith('.mp3'):
            # Convert to absolute path
            filepath = os.path.abspath(filename)
            logger.info(f"New file detected: {filepath}")
            # Small delay to ensure file write is complete
            time.sleep(2) 
            self.scribe.process_file(filepath)

class Scribe:
    def __init__(self, config, dry_run=False, template_name="default"):
        self.config = config
        self.dry_run = dry_run
        self.template_name = template_name
        self.setup_gemini()
        self.processing_files = set()

    def setup_gemini(self):
        api_key = os.getenv("GEMINI_API_KEY") or self.config['gemini']['api_key']
        if not api_key or api_key == "YOUR_KEY_HERE":
             logger.warning("Gemini API Key not found in env or config. Please set it.")
        genai.configure(api_key=api_key)
        
        try:
            system_instruction = get_system_prompt(self.template_name)
        except FileNotFoundError as e:
            logger.error(f"Template error: {e}")
            # Fallback to default or exit? 
            # For robustness, let's try default, if that fails, we crash.
            logger.warning("Falling back to 'default' template.")
            system_instruction = get_system_prompt("default")

        self.model = genai.GenerativeModel(
            model_name=self.config['gemini']['model'],
            system_instruction=system_instruction
        )

    def watch(self, input_path=None):
        """Starts the daemon to watch for new files."""
        input_dir = input_path or self.config['paths']['input']
        os.makedirs(input_dir, exist_ok=True)
        
        event_handler = AudioHandler(self)
        observer = Observer()
        observer.schedule(event_handler, input_dir, recursive=False)
        observer.start()
        
        logger.info(f"Scribe is listening in {input_dir}...")
        if self.dry_run:
            logger.info("DRY RUN MODE: No API calls will be made.")
        logger.info("Press Ctrl+C to stop.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            logger.info("Stopping Scribe...")
        
        observer.join()

    def process_all(self, input_path=None):
        """Processes all existing files in the input directory."""
        input_dir = input_path or self.config['paths']['input']
        os.makedirs(input_dir, exist_ok=True)
        
        logger.info(f"Scanning {input_dir} for files...")
        if self.dry_run:
            logger.info("DRY RUN MODE: No API calls will be made.")

        files = [f for f in os.listdir(input_dir) if f.lower().endswith('.mp3')]
        
        if not files:
            logger.info("No files found to process.")
            return

        for filename in files:
            filepath = os.path.join(input_dir, filename)
            self.process_file(filepath)

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
        logger.info(f"Using template: {self.template_name}")

        if self.dry_run:
            logger.info(f"[DRY RUN] Would process {filename}")
            logger.info(f"[DRY RUN] Would compress -> upload -> generate -> save")
            self.processing_files.remove(filepath)
            return

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
        day = now.strftime("%d")
        
        results_dir = self.config['paths']['results']
        target_dir = os.path.join(results_dir, year, month, day, folder_name)
        os.makedirs(target_dir, exist_ok=True)
        
        # Save compressed audio
        shutil.copy2(compressed_path, os.path.join(target_dir, "compressed.ogg"))
        
        # Process text content
        text_content = response.text
        
        parts = text_content.split("---SPLIT_OUTPUT_HERE---")
        
        raw_json_str = ""
        clean_markdown = ""
        
        if len(parts) >= 2:
            raw_json_str = parts[0].strip()
            clean_markdown = parts[1].strip()
        else:
            logger.warning("Could not split response into two parts. Saving all to clean transcript.")
            clean_markdown = text_content

        # Save Raw Transcript (JSON)
        raw_data = []
        try:
            # Clean up potential markdown code blocks if the model ignored instructions
            cleaned_json_str = raw_json_str.replace("```json", "").replace("```", "").strip()
            if cleaned_json_str:
                raw_data = json.loads(cleaned_json_str)
            
            with open(os.path.join(target_dir, "transcript_raw.json"), "w") as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse raw transcript JSON: {e}")
            # Fallback: Save the raw string to a text file for debugging
            with open(os.path.join(target_dir, "transcript_raw_error.txt"), "w") as f:
                f.write(raw_json_str)

        # Add metadata to clean transcript
        meta_header = f"**Original File Date:** {creation_date_str}\n**Processed Date:** {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        final_clean_content = meta_header + clean_markdown

        # Save Clean Transcript (Markdown)
        with open(os.path.join(target_dir, "transcript_clean.md"), "w") as f:
            f.write(final_clean_content)
            
        # Calculate stats
        end_time = time.time()
        duration = end_time - start_time
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        input_rate = self.config.get('pricing', {}).get('input_per_1m', 0.075)
        output_rate = self.config.get('pricing', {}).get('output_per_1m', 0.30)
        cost = get_cost_estimate(input_tokens, output_tokens, input_rate, output_rate)
        
        # Generate and save metadata
        self.save_metadata(
            target_dir, 
            original_path, 
            compressed_path, 
            start_time, 
            duration, 
            input_tokens, 
            output_tokens, 
            cost,
            self.config['gemini']['model']
        )
        
        # Print to console
        print("\n" + "="*30)
        print(f"DONE: {filename}")
        print(f"Original Date: {creation_date_str}")
        print(f"Time: {duration:.2f}s")
        print(f"Tokens: {input_tokens} in / {output_tokens} out")
        print(f"Cost: {cost}")
        print("="*30 + "\n")

    def save_metadata(self, target_dir, original_path, compressed_path, start_time, process_duration, input_tokens, output_tokens, cost, model_name):
        meta = {
            "id": str(uuid.uuid4()),
            "file": {
                "original_name": os.path.basename(original_path),
                "created_at": datetime.fromtimestamp(os.path.getctime(original_path)).isoformat(),
                "size_bytes": os.path.getsize(original_path),
                "checksum_sha256": self.calculate_checksum(compressed_path),
                "duration_seconds": self.get_audio_duration(compressed_path)
            },
            "processing": {
                "timestamp_start": datetime.fromtimestamp(start_time).isoformat(),
                "duration_seconds": round(process_duration, 2),
                "model": model_name,
                "tokens": {
                    "input": input_tokens,
                    "output": output_tokens
                },
                "cost_usd": cost
            },
            "content": {
                "language": "auto", 
                "device_id": None,
                "source": None
            }
        }
        
        with open(os.path.join(target_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    def calculate_checksum(self, filepath):
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def get_audio_duration(self, filepath):
        try:
            cmd = [
                'ffprobe', 
                '-v', 'error', 
                '-show_entries', 'format=duration', 
                '-of', 'default=noprint_wrappers=1:nokey=1', 
                filepath
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")
            return 0.0

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
