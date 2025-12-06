"""Constants used throughout the Amanu application."""

# Output filenames
COMPRESSED_AUDIO_FILENAME = "compressed.ogg"
RAW_TRANSCRIPT_FILENAME = "transcript_raw.json"
CLEAN_TRANSCRIPT_FILENAME = "transcript_clean.md"
RAW_TRANSCRIPT_ERROR_FILENAME = "transcript_raw_error.txt"

# Timeouts and intervals (in seconds)
GEMINI_PROCESSING_POLL_INTERVAL = 2
FILE_WAIT_TIMEOUT = 60
FILE_STABILIZATION_CHECK_INTERVAL = 1
CHECKSUM_BLOCK_SIZE = 4096

# Audio processing parameters
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_BITRATE = "24k"
DEFAULT_AUDIO_FORMAT = "ogg"
DEFAULT_AUDIO_CODEC = "libopus"

# File extensions
MP3_EXTENSION = ".mp3"
OGG_EXTENSION = ".ogg"
