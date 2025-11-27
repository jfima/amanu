# Getting Started with Amanu on macOS

Welcome! This guide will help you set up Amanu on your Mac from scratch. No prior experience needed.

---

## 📋 What You'll Need

- A Mac running macOS 10.15 or later
- Internet connection
- 15-20 minutes

---

## Step 1: Install Homebrew

Homebrew is a package manager that makes installing software easy.

1. Open **Terminal**:
   - Press `Cmd + Space`
   - Type "Terminal"
   - Press Enter

2. Copy and paste this command:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

3. Press Enter and follow the prompts
4. Enter your Mac password when asked (you won't see it typing - that's normal!)

---

## Step 2: Install Python and FFmpeg

In Terminal, run these commands one by one:

```bash
# Install Python 3.11
brew install python@3.11

# Install FFmpeg (for audio processing)
brew install ffmpeg
```

### Verify Installation

```bash
python3.11 --version
ffmpeg -version
```

You should see version numbers for both.

---

## Step 3: Install Amanu

1. Download Amanu:
   ```bash
   cd ~
   git clone https://github.com/jfima/amanu
   cd amanu
   ```

   **Don't have git?** Install it first:
   ```bash
   brew install git
   ```

2. Install Amanu:
   ```bash
   python3.11 -m pip install -e .
   ```

---

## Step 4: Get Your Google Gemini API Key

1. Open Safari and go to: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Click the copy icon to copy your key

**Keep this key safe!** You'll need it in the next step.

---

## Step 5: Run the Setup Wizard

In Terminal, type:

```bash
amanu setup
```

The beautiful wizard will guide you through:

### 🔑 API Key
Paste the key you copied (press `Cmd + V`)

### 🤖 Model Selection
Use arrow keys to choose:
- **Gemini 2.0 Flash** (Recommended) - Fastest and cheapest
- **Gemini 2.5 Flash** - Better quality
- **Gemini 2.5 Pro** - Best quality, higher cost

### 🌍 Language
- Choose "Auto" for automatic detection
- Or select your primary language

### 📁 Folders
Default locations work great:
- `~/amanu/scribe-in` - Drop files here
- `~/amanu/scribe-out` - Results appear here

### 🐛 Debug Mode
Choose "No" unless you're troubleshooting

---

## Step 6: Process Your First Audio File

1. Put an audio file somewhere (MP3, WAV, M4A, etc.)

2. In Terminal:
   ```bash
   amanu run ~/Downloads/your-audio.mp3
   ```
   
   Replace with your actual file path. **Tip**: Drag the file into Terminal to auto-fill the path!

3. Watch the magic happen ✨

4. Find results in `~/amanu/scribe-out/YYYY/MM/DD/`

---

## 🎉 You're Done!

You now have:
- ✅ A full transcript in Markdown
- ✅ A summary with key points
- ✅ Speaker-separated dialogue
- ✅ Optional PDF and SRT files

---

## 💡 Pro Tips

### Use Watch Mode
```bash
amanu watch
```
Drop files into `~/amanu/scribe-in/`, get automatic processing!

### Create an Alias
Add to your `~/.zshrc`:
```bash
alias transcribe='amanu run'
```

Then just:
```bash
transcribe my-audio.mp3
```

### Check Costs
```bash
amanu report --days 7
```

### Reconfigure Anytime
```bash
amanu setup
```

---

## 🆘 Troubleshooting

### "command not found: amanu"
Try:
```bash
python3.11 -m pip install --upgrade pip
python3.11 -m pip install -e ~/amanu
```

### "FFmpeg not found"
```bash
brew reinstall ffmpeg
```

### "Permission denied"
Add `sudo` before the command:
```bash
sudo pip install -e .
```

### "API Key invalid"
- Make sure you copied the entire key
- No extra spaces or line breaks
- Generate a new key if needed

---

## 🎨 macOS-Specific Features

### Drag & Drop
Create a simple app using Automator:
1. Open Automator
2. New Document → Application
3. Add "Run Shell Script"
4. Paste:
   ```bash
   for f in "$@"
   do
       /usr/local/bin/amanu run "$f"
   done
   ```
5. Save as "Transcribe.app"

Now drag audio files onto the app icon!

### Finder Integration
Right-click any audio file → Services → "Transcribe with Amanu"

---

## 📚 Next Steps

- [Learn about all features](./features.md)
- [Customize your templates](./customization.md)
- [Advanced configuration](./configuration.md)

---

Need help? Open an issue on [GitHub](https://github.com/jfima/amanu/issues)!
