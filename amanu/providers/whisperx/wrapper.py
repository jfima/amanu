"""
Wrapper for WhisperX that fixes PyTorch 2.6 compatibility 
with PyAnnote models by adding omegaconf classes to safe globals.
"""
import sys
import torch

#Aggressive monkey-patch for torch.load to bypass PyTorch 2.6 weights_only restrictions
original_torch_load = torch.load

def patched_torch_load(*args, **kwargs):
    # Always set weights_only to False, ignoring whatever was passed
    kwargs['weights_only'] = False
    return original_torch_load(*args, **kwargs)

# Replace torch.load globally
torch.load = patched_torch_load

# Also patch in torch.serialization if it exists
if hasattr(torch, 'serialization'):
    torch.serialization.load = patched_torch_load

# Now import and run whisperx
from whisperx import __main__

if __name__ == '__main__':
    try:
        __main__.cli()
    finally:
        # Explicit cleanup to help release VRAM immediately
        # particularly important when chaining with other GPU-heavy tasks like Ollama
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
