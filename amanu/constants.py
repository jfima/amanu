"""Constants used throughout the Amanu application."""

# Response delimiters
RESPONSE_DELIMITER = "---SPLIT_OUTPUT_HERE---"

# Output filenames
COMPRESSED_AUDIO_FILENAME = "compressed.ogg"
RAW_TRANSCRIPT_FILENAME = "transcript_raw.json"
CLEAN_TRANSCRIPT_FILENAME = "transcript_clean.md"
METADATA_FILENAME = "meta.json"
RAW_TRANSCRIPT_ERROR_FILENAME = "transcript_raw_error.txt"

# Timeouts and intervals (in seconds)
FILE_WAIT_TIMEOUT = 10
FILE_STABILIZATION_CHECK_INTERVAL = 1
GEMINI_PROCESSING_POLL_INTERVAL = 2

# Audio processing parameters
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_BITRATE = "24k"
DEFAULT_AUDIO_FORMAT = "ogg"
DEFAULT_AUDIO_CODEC = "libopus"

# File operations
FILE_WAIT_TIMEOUT = 60  # seconds
FILE_STABILIZATION_CHECK_INTERVAL = 1  # seconds
CHECKSUM_BLOCK_SIZE = 4096

# File extensions
MP3_EXTENSION = ".mp3"
OGG_EXTENSION = ".ogg"
