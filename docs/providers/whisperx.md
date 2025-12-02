# WhisperX Provider Integration Guide

## Overview

The WhisperX provider enables high-quality speech transcription with speaker diarization support. This integration uses the [WhisperX](https://github.com/m-bain/whisperX) library, which provides:

- Fast batch transcription with GPU acceleration
- Word-level timestamps
- Speaker diarization (identifying who spoke when)
- Support for multiple languages

## Installation

### Prerequisites

1. **Python 3.11+** with pip
2. **CUDA-capable GPU** (recommended for performance)
3. **CUDA Toolkit 12.x** installed on your system
4. **cuDNN 9** libraries

### Step 1: Install WhisperX

```bash
python3.11 -m pip install whisperx
```

### Step 2: Install PyTorch with CUDA Support

```bash
python3.11 -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
```

**Note:** Adjust `cu124` to match your CUDA version (e.g., `cu118` for CUDA 11.8).

### Step 3: Install cuDNN 9 (Linux/WSL2)

For Ubuntu/Debian-based systems:

```bash
sudo apt-get update
sudo apt-get install -y cudnn9-cuda-12
```

**Important for WSL2 users:** Ensure both CUDA drivers and cuDNN libraries are accessible. See [Troubleshooting](#troubleshooting) section below.

### Step 4: Configure Amanu

Add WhisperX configuration to your `config.yaml`:

```yaml
transcribe:
  provider: whisperx
  model: large-v2

providers:
  whisperx:
    python_executable: python3.11
    device: cuda
    compute_type: float16
    batch_size: 16
    language: Russian  # or English, Spanish, etc.
    enable_diarization: true
    hf_token: your_huggingface_token_here  # Required for diarization
    models:
      - name: large-v2
        context_window:
          input_tokens: 0
          output_tokens: 0
        cost_per_1M_tokens_usd:
          input: 0.0
          output: 0.0
```

### Step 5: Get HuggingFace Token (for Diarization)

Speaker diarization requires access to PyAnnote models on HuggingFace:

1. Create an account at [huggingface.co](https://huggingface.co)
2. Go to [Settings → Access Tokens](https://huggingface.co/settings/tokens)
3. Create a new token with read permissions
4. Accept the user agreement for [pyannote/speaker-diarization](https://huggingface.co/pyannote/speaker-diarization)
5. Add the token to your `config.yaml` as shown above

## Configuration Options

### Core Settings

- **`python_executable`**: Path to Python interpreter (default: `python3`)
- **`device`**: Compute device - `cuda` or `cpu` (default: `cuda`)
- **`compute_type`**: Precision - `float16`, `float32`, or `int8` (default: `float16`)
- **`batch_size`**: Number of audio chunks to process in parallel (default: `16`)

### Language Settings

- **`language`**: Target language for transcription
  - Use full name (e.g., `Russian`, `English`) or ISO code (e.g., `ru`, `en`)
  - Set to `null` or omit for automatic language detection
  - Specifying language improves accuracy and speed

### Diarization Settings

- **`enable_diarization`**: Enable speaker identification (default: `false`)
- **`hf_token`**: HuggingFace access token (required when `enable_diarization: true`)

### Model Configuration

WhisperX supports the following Whisper models:

- `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3`

Larger models provide better accuracy but require more VRAM and processing time.

## Troubleshooting

### Issue 1: PyTorch 2.6+ `weights_only` Error

**Symptom:**
```
WeightsUnpickler error: Unsupported global: GLOBAL omegaconf.listconfig.ListConfig
```

**Solution:**
This is automatically handled by the `whisperx_wrapper.py` script included with the provider. The wrapper monkey-patches `torch.load` to allow loading PyAnnote models.

**Technical Details:**
PyTorch 2.6+ changed the default behavior of `torch.load()` to use `weights_only=True` for security. However, PyAnnote models use OmegaConf configuration objects that are not allowed by default. The wrapper script overrides this restriction.

### Issue 2: cuDNN Library Not Found (WSL2)

**Symptom:**
```
Unable to load any of {libcudnn_cnn.so.9.1.0, libcudnn_cnn.so.9.1, ...}
Invalid handle. Cannot load symbol cudnnCreateConvolutionDescriptor
```

**Solution:**
The provider automatically sets `LD_LIBRARY_PATH` to include both WSL2 CUDA drivers and system libraries:

```python
env['LD_LIBRARY_PATH'] = "/usr/lib/wsl/lib:/usr/lib/x86_64-linux-gnu:..."
```

**Manual Verification:**
```bash
# Check if cuDNN libraries are installed
find /usr/lib -name "libcudnn_cnn.so*"

# Should output:
# /usr/lib/x86_64-linux-gnu/libcudnn_cnn.so.9
# /usr/lib/x86_64-linux-gnu/libcudnn_cnn.so.9.16.0
```

If libraries are missing, reinstall cuDNN:
```bash
sudo apt-get install -y cudnn9-cuda-12
```

### Issue 3: No CUDA Device Detected

**Symptom:**
```
RuntimeError: CUDA failed with error no CUDA-capable device is detected
```

**Solutions:**

1. **Verify CUDA is available:**
   ```bash
   python3.11 -c "import torch; print(torch.cuda.is_available())"
   ```

2. **Check NVIDIA drivers (WSL2):**
   ```bash
   nvidia-smi
   ```

3. **Reinstall PyTorch with CUDA support:**
   ```bash
   python3.11 -m pip install torch torchaudio --force-reinstall --index-url https://download.pytorch.org/whl/cu124
   ```

4. **Fallback to CPU mode:**
   In `config.yaml`, set:
   ```yaml
   providers:
     whisperx:
       device: cpu
   ```

### Issue 4: Module Import Conflict

**Symptom:**
```
ImportError: attempted relative import with no known parent package
```

**Cause:**
The provider file was named `whisperx.py`, which conflicts with the installed `whisperx` package when the wrapper script tries to import it.

**Solution:**
This has been resolved by using the wrapper script (`whisperx_wrapper.py`) which imports the installed package correctly.

### Issue 5: Diarization Fails or Returns Single Speaker

**Possible Causes:**

1. **Missing HuggingFace token:**
   - Ensure `hf_token` is set in config
   - Verify token has access to PyAnnote models

2. **Audio quality issues:**
   - Diarization works best with clear audio
   - Multiple speakers should have distinct voices
   - Minimum audio length: ~10 seconds

3. **Model compatibility:**
   - PyAnnote models were trained on older PyTorch versions
   - Warnings about version mismatches are normal and usually harmless

## Architecture

### Component Overview

```
amanu/providers/
├── whisperx_provider.py  # Main provider implementation
└── whisperx_wrapper.py   # PyTorch compatibility wrapper
```

**Note:** The provider file is named `whisperx_provider.py` (not `whisperx.py`) to avoid import conflicts with the installed `whisperx` package when the wrapper script imports it.

### Execution Flow

1. **Provider Initialization** (`WhisperXProvider.__init__`)
   - Verifies WhisperX installation
   - Loads configuration

2. **Transcription** (`WhisperXProvider.transcribe`)
   - Determines language settings
   - Calls `_run_whisperx` subprocess
   - Parses JSON output
   - Calculates tokens and costs

3. **Subprocess Execution** (`WhisperXProvider._run_whisperx`)
   - Builds command with all parameters
   - Sets environment variables (LD_LIBRARY_PATH)
   - Runs `whisperx_wrapper.py` script
   - Handles errors and output

4. **Wrapper Script** (`whisperx_wrapper.py`)
   - Monkey-patches `torch.load` for PyTorch 2.6+ compatibility
   - Imports and runs WhisperX CLI
   - Returns transcription results

### Output Format

WhisperX generates JSON with the following structure:

```json
{
  "segments": [
    {
      "text": "Transcribed text",
      "start": 2.967,
      "end": 31.672,
      "speaker": "SPEAKER_00"
    }
  ],
  "word_segments": [
    {
      "word": "Transcribed",
      "start": 2.967,
      "end": 3.307,
      "score": 0.774,
      "speaker": "SPEAKER_00"
    }
  ],
  "language": "ru"
}
```

The provider transforms this into Amanu's internal format:

```python
{
    "speaker_id": "SPEAKER_00",
    "start_time": 2.967,
    "end_time": 31.672,
    "text": "Transcribed text",
    "confidence": 1.0
}
```

## Performance Optimization

### GPU Memory Management

- **Reduce `batch_size`** if you encounter OOM (Out of Memory) errors
- **Use `float16`** instead of `float32` for compute_type to save VRAM
- **Monitor GPU usage:**
  ```bash
  watch -n 1 nvidia-smi
  ```

### Speed vs. Quality Trade-offs

| Model | VRAM | Speed | Quality |
|-------|------|-------|---------|
| tiny | ~1GB | Fastest | Basic |
| base | ~1GB | Very Fast | Good |
| small | ~2GB | Fast | Better |
| medium | ~5GB | Moderate | Great |
| large-v2 | ~10GB | Slow | Excellent |
| large-v3 | ~10GB | Slow | Best |

### Batch Processing

For multiple files, process them sequentially to avoid memory issues:

```bash
for file in *.mp3; do
    amanu scribe "$file"
done
```

## Known Limitations

1. **Model Compatibility:**
   - WhisperX uses PyAnnote 0.0.1 models with PyTorch 2.8+
   - Version mismatch warnings are expected and usually harmless

2. **Diarization Accuracy:**
   - Works best with 2-4 speakers
   - May struggle with overlapping speech
   - Requires clear audio quality

3. **Language Detection:**
   - Automatic detection adds processing time
   - Specifying language improves accuracy

4. **WSL2 Specific:**
   - Requires proper LD_LIBRARY_PATH configuration
   - CUDA drivers must be accessible from WSL2

## Support and Resources

- **WhisperX GitHub:** https://github.com/m-bain/whisperX
- **PyAnnote:** https://github.com/pyannote/pyannote-audio
- **Amanu Issues:** Report integration-specific problems to the Amanu repository

## Version History

- **v1.0.0** (2024-12-01): Initial WhisperX integration
  - PyTorch 2.6+ compatibility via wrapper script
  - WSL2 cuDNN path resolution
  - Speaker diarization support
  - Multi-language support
