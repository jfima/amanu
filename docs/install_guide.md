# Instruction 1: Installing Whisper.cpp (Windows/WSL & macOS)

This guide covers the installation of `whisper.cpp` with GPU acceleration. The goal is to build the tool and make it globally accessible from any directory in your terminal.

## Part A: Windows 11 (via WSL2) with NVIDIA CUDA

### 1. Prerequisites (Windows Side)
*   **NVIDIA Drivers**: Install the latest NVIDIA drivers for your GPU on Windows. WSL2 uses these drivers directly.
*   **WSL2**: Ensure WSL2 is installed (usually Ubuntu).

### 2. Prerequisites (WSL Side)
Open your WSL terminal (Ubuntu) and run the following to install build tools and CUDA toolkit:

```bash
sudo apt update
sudo apt install -y build-essential cmake git

# Install CUDA Toolkit (required for nvcc compiler)
sudo apt install -y nvidia-cuda-toolkit
```

> **Important Compatibility Note**: If you encounter build errors related to `std_function` or "parameter packs", your GCC compiler might be too new for the installed CUDA version. In that case, install GCC 10:
> ```bash
> sudo apt install -y gcc-10 g++-10
> ```

### 3. Clone and Build
Clone the repository and build with CUDA support.

```bash
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp

# Clean any previous builds
rm -rf build

# Configure with CMake
# -DGGML_CUDA=1: Enables CUDA support
# -DCMAKE_CUDA_ARCHITECTURES=86: Fallback architecture for RTX 3000/4000 series if using older CUDA toolkits
# Note: If you installed GCC 10 above, prepend: CC=gcc-10 CXX=g++-10 CMAKE_CUDA_HOST_COMPILER=g++-10
export CC=gcc-10 CXX=g++-10 
cmake -B build -DGGML_CUDA=1 -DCMAKE_CUDA_ARCHITECTURES=86 -DCMAKE_CUDA_HOST_COMPILER=g++-10

# Build release version
cmake --build build -j --config Release
```

### 4. Download Models
The model files are part of the installation. Download the desired model (e.g., `large-v3` for best quality).

```bash
bash ./models/download-ggml-model.sh large-v3
```

### 5. Make Globally Accessible
To run `whisper-cli` from any folder, create a symbolic link to `/usr/local/bin`.

```bash
# Get the absolute path to your current directory
CURRENT_DIR=$(pwd)

# Link the executable
sudo ln -s "$CURRENT_DIR/build/bin/whisper-cli" /usr/local/bin/whisper-cli

# Verify it works from anywhere
cd ~
whisper-cli --help
```

---

## Part B: macOS (Apple Silicon)

Installation on macOS is straightforward as Metal (GPU) support is often enabled by default or easily toggled.

### 1. Prerequisites
*   **Xcode Command Line Tools**:
    ```bash
    xcode-select --install
    ```
*   **CMake**:
    ```bash
    brew install cmake
    ```

### 2. Clone and Build

```bash
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp

# Build with CoreML/Metal support
# The Makefile usually handles this automatically on macOS
make -j
```

### 3. Download Models

```bash
bash ./models/download-ggml-model.sh large-v3
```

### 4. Make Globally Accessible

```bash
# Get the absolute path
CURRENT_DIR=$(pwd)

# Link the executable
sudo ln -s "$CURRENT_DIR/main" /usr/local/bin/whisper-cli

# Verify
whisper-cli --help
```
