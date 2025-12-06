# Ollama Provider

The Ollama provider enables local AI model processing with privacy and cost control through [Ollama](https://ollama.ai/). This provider supports both transcription and refinement capabilities using locally hosted models.

## Overview

Ollama is a platform for running large language models locally. The Amanu Ollama provider integrates with Ollama to provide:

- **Local audio transcription** using Whisper-compatible models
- **Multimodal transcription** via LLaVA models with spectrogram conversion
- **Text refinement and analysis** using large language models
- **Automatic model management** with pull-on-demand functionality
- **Cost-free processing** (no API costs, only computational resources)

## Prerequisites

### 1. Ollama Installation

Install Ollama on your system:

```bash
# macOS
curl -fsSL https://ollama.ai/install.sh | sh

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Or download from https://ollama.ai/download
```

### 2. Start Ollama Server

```bash
# Start the Ollama server
ollama serve

# By default, it runs on http://localhost:11434
```

### 3. Docker Configuration

For Docker setups, use `host.docker.internal:11434` as the base URL in configuration.

### 4. Python Dependencies

Install additional dependencies for multimodal transcription:

```bash
pip install librosa matplotlib numpy
```

## Configuration

### Basic Configuration

Add to your `config.yaml`:

```yaml
transcribe:
  provider: ollama
  model: whisper-large-v3-turbo

refine:
  provider: ollama
  model: gpt-oss:20b

providers:
  ollama:
    base_url: "http://host.docker.internal:11434"
    timeout: 600
    auto_pull_models: true
    use_gpu: true
```

### Advanced Configuration

```yaml
providers:
  ollama:
    base_url: "http://host.docker.internal:11434"
    timeout: 600
    auto_pull_models: true
    use_gpu: true
    gpu_memory_limit: 24000  # 24GB in MB
    preferred_quantization: "q4_0"
    max_retries: 3
    retry_delay: 5
    transcription_model: "whisper-large-v3-turbo"
    refinement_model: "gpt-oss:20b"
```

### Environment Variables

You can also configure using environment variables:

```bash
export OLLAMA_BASE_URL="http://host.docker.internal:11434"
export OLLAMA_TIMEOUT="600"
export OLLAMA_AUTO_PULL_MODELS="true"
export OLLAMA_USE_GPU="true"
```

## Available Models

### Transcription Models

| Model | Description | VRAM Required | Speed | Accuracy |
|-------|-------------|---------------|-------|----------|
| `whisper-large-v3-turbo` | Fast and accurate speech recognition | ~1.5GB | Fast | High |
| `whisper-large-v3` | Most accurate speech recognition | ~1.5GB | Medium | Very High |
| `llava-llama3:8b` | Multimodal via spectrograms | ~8GB | Medium | Medium |
| `bakllava:7b` | Compact multimodal | ~5GB | Fast | Medium |

### Refinement Models

| Model | Description | VRAM Required | Context | Specialization |
|-------|-------------|---------------|---------|----------------|
| `gpt-oss:20b` | Large language model for analysis | ~20GB | 8K | General analysis |
| `llama3.1:8b` | Fast and efficient | ~8GB | 128K | Quick processing |
| `qwen2.5:14b` | Multilingual with Russian support | ~10GB | 32K | Multilingual |
| `llama3.1:70b` | High-capability analysis | ~24GB | 128K | Complex analysis |

## Usage Examples

### Basic Audio Processing

```bash
# Process audio with Ollama
amanu run audio.mp3

# Use specific models
amanu run audio.mp3 --transcribe-model whisper-large-v3 --refine-model llama3.1:8b
```

### Manual Model Management

```bash
# Pull models manually
ollama pull whisper-large-v3-turbo
ollama pull gpt-oss:20b

# List available models
ollama list

# Remove unused models
ollama remove model-name
```

### Configuration for Different Use Cases

#### For Maximum Accuracy
```yaml
transcribe:
  provider: ollama
  model: whisper-large-v3

refine:
  provider: ollama
  model: gpt-oss:20b
```

#### For Speed and Efficiency
```yaml
transcribe:
  provider: ollama
  model: whisper-large-v3-turbo

refine:
  provider: ollama
  model: llama3.1:8b
```

#### For Multilingual Content
```yaml
transcribe:
  provider: ollama
  model: whisper-large-v3-turbo

refine:
  provider: ollama
  model: qwen2.5:14b
```

## Transcription Approaches

### 1. Whisper-based Transcription

Uses Whisper-compatible models for direct audio-to-text conversion:

```yaml
transcribe:
  provider: ollama
  model: whisper-large-v3-turbo
```

**Advantages:**
- High accuracy
- Fast processing
- Language detection
- Timestamp support

**Limitations:**
- Requires Whisper-compatible models
- Limited to speech recognition

### 2. Multimodal Transcription

Uses LLaVA models with spectrogram conversion:

```yaml
transcribe:
  provider: ollama
  model: llava-llama3:8b
```

**Advantages:**
- Can handle non-speech audio
- Visual analysis capabilities
- Flexible model choice

**Limitations:**
- Requires additional dependencies
- Slower processing
- May have lower accuracy for pure speech

## Performance Optimization

### GPU Memory Management

For 24GB VRAM systems:

```yaml
providers:
  ollama:
    use_gpu: true
    gpu_memory_limit: 24000  # 24GB in MB
    preferred_quantization: "q4_0"
```

### Model Quantization

Choose appropriate quantization based on your VRAM:

- `q4_0`: 4-bit quantization, good balance of quality and memory
- `q5_1`: 5-bit quantization, better quality
- `q8_0`: 8-bit quantization, best quality but more memory

### Batch Processing

For processing multiple files:

```bash
# Process multiple files in sequence
for file in *.mp3; do
    amanu run "$file"
done
```

## Troubleshooting

### Common Issues

#### 1. Connection Failed

**Error:** `Cannot connect to Ollama server`

**Solution:**
- Ensure Ollama is running: `ollama serve`
- Check URL configuration
- Verify Docker networking if using containers

#### 2. Model Not Found

**Error:** `Model not found and auto_pull is disabled`

**Solution:**
- Enable auto-pull: `auto_pull_models: true`
- Pull manually: `ollama pull model-name`
- Check model name spelling

#### 3. Out of Memory

**Error:** GPU memory insufficient

**Solution:**
- Use smaller models
- Enable quantization
- Set GPU memory limit
- Use CPU processing: `use_gpu: false`

#### 4. Slow Processing

**Causes and Solutions:**
- Large model: Use smaller or quantized models
- CPU processing: Enable GPU acceleration
- Long audio: Consider chunking or compression

### Debug Mode

Enable debug logging:

```yaml
debug: true
providers:
  ollama:
    timeout: 1200  # Increase timeout for debugging
```

### Testing

Run the verification script:

```bash
python tests/verify_ollama.py
```

## Integration with Other Providers

You can mix Ollama with other providers:

```yaml
transcribe:
  provider: ollama
  model: whisper-large-v3-turbo

refine:
  provider: openrouter
  model: google/gemini-2.0-flash-lite-001
```

## Advanced Features

### Custom Model Integration

Add custom models to your configuration:

```yaml
providers:
  ollama:
    custom_models:
      - name: "my-custom-model"
        type: "refinement"
        context_window: {input_tokens: 4096, output_tokens: 2048}
```

### Model-Specific Prompts

Customize prompts for specific models:

```yaml
providers:
  ollama:
    transcription_prompt: "Please transcribe this audio accurately in {language}."
    refinement_prompt: "Analyze this transcript and extract key insights."
```

## API Reference

### OllamaConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | str | `http://host.docker.internal:11434` | Ollama server URL |
| `timeout` | int | `600` | Request timeout in seconds |
| `auto_pull_models` | bool | `true` | Automatically pull missing models |
| `use_gpu` | bool | `true` | Use GPU acceleration |
| `gpu_memory_limit` | int | `null` | GPU memory limit in MB |
| `preferred_quantization` | str | `q4_0` | Model quantization preference |
| `max_retries` | int | `3` | Maximum retry attempts |
| `retry_delay` | int | `5` | Delay between retries |

### Model Specifications

Each model includes:

- `name`: Model identifier
- `type`: `transcription`, `refinement`, or `multimodal`
- `context_window`: Input/output token limits
- `cost_per_1M_tokens_usd`: Always `0.0` for local models
- `description`: Model capabilities and use cases

## Contributing

To contribute to the Ollama provider:

1. Test with different models and configurations
2. Report performance characteristics
3. Suggest optimizations
4. Submit pull requests for enhancements

## License

This provider follows the same license as Amanu. Ollama models may have their own licenses - check individual model documentation.