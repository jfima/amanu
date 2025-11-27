# Getting Started with Amanu on Windows 11

Welcome! This guide will help you set up Amanu on Windows 11 from scratch. No prior experience needed.

---

## 📋 What You'll Need

- A Windows 11 computer
- Internet connection
- 15-20 minutes

---

## Step 1: Install Python

### Download Python

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Click the big yellow "Download Python" button
3. Run the downloaded installer

### Important: Check "Add Python to PATH"

⚠️ **Critical Step**: When the installer opens, check the box that says **"Add Python to PATH"** at the bottom!

![Python installer](https://docs.python.org/3/_images/win_installer.png)

4. Click "Install Now"
5. Wait for installation to complete
6. Click "Close"

### Verify Installation

1. Press `Win + R`
2. Type `cmd` and press Enter
3. In the black window, type:
   ```cmd
   python --version
   ```
4. You should see something like `Python 3.11.x`

---

## Step 2: Install FFmpeg

FFmpeg is needed to process audio files.

### Easy Method (Using Chocolatey)

1. Open PowerShell **as Administrator**:
   - Press `Win + X`
   - Click "Windows PowerShell (Admin)" or "Terminal (Admin)"

2. Install Chocolatey (package manager):
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   ```

3. Install FFmpeg:
   ```powershell
   choco install ffmpeg
   ```

4. Type `Y` when asked to confirm

### Verify FFmpeg

Close and reopen PowerShell, then type:
```powershell
ffmpeg -version
```

You should see version information.

---

## Step 3: Install Amanu

1. Download Amanu:
   - Go to [github.com/jfima/amanu](https://github.com/jfima/amanu)
   - Click the green "Code" button
   - Click "Download ZIP"

2. Extract the ZIP file:
   - Right-click the downloaded file
   - Click "Extract All"
   - Choose a location (e.g., `C:\Users\YourName\amanu`)

3. Open PowerShell in the amanu folder:
   - Open the extracted folder
   - Hold `Shift` and right-click in the folder
   - Click "Open PowerShell window here"

4. Install Amanu:
   ```powershell
   pip install -e .
   ```

---

## Step 4: Get Your Google Gemini API Key

1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (it looks like: `AIzaSy...`)

**Keep this key safe!** You'll need it in the next step.

---

## Step 5: Run the Setup Wizard

In PowerShell (in the amanu folder), type:

```powershell
amanu setup
```

The wizard will ask you:

### 🔑 API Key
Paste the key you copied in Step 4

### 🤖 Model Selection
- **Gemini 2.0 Flash** (Recommended) - Fastest and cheapest
- **Gemini 2.5 Flash** - Better quality
- **Gemini 2.5 Pro** - Best quality, higher cost

### 🌍 Language
Choose "Auto" unless you know all your audio is in one language

### 📁 Folders
Accept the defaults or customize where files go

### 🐛 Debug Mode
Choose "No" unless you're troubleshooting

---

## Step 6: Process Your First Audio File

1. Put an audio file (MP3, WAV, etc.) somewhere easy to find

2. In PowerShell, type:
   ```powershell
   amanu run "C:\path\to\your\audio.mp3"
   ```
   
   Replace the path with your actual file location.

3. Wait for processing (you'll see progress)

4. Find your results in `scribe-out\YYYY\MM\DD\`

---

## 🎉 You're Done!

You now have:
- ✅ A full transcript in Markdown
- ✅ A summary with key points
- ✅ Speaker-separated dialogue
- ✅ Optional PDF and SRT files

---

## 💡 Tips

### Use Watch Mode
```powershell
amanu watch
```
Drop files into `scribe-in\`, get automatic processing!

### Check Costs
```powershell
amanu report --days 7
```
See how much you've spent

### Reconfigure Anytime
```powershell
amanu setup
```
Change settings without starting over

---

## 🆘 Troubleshooting

### "amanu is not recognized"
- Make sure you installed Python with "Add to PATH" checked
- Restart PowerShell

### "FFmpeg not found"
- Restart PowerShell after installing FFmpeg
- Try the manual installation method

### "API Key invalid"
- Double-check you copied the entire key
- Make sure there are no extra spaces
- Generate a new key if needed

---

## 📚 Next Steps

- [Learn about all features](./features.md)
- [Customize your templates](./customization.md)
- [Advanced configuration](./configuration.md)

---

Need help? Open an issue on [GitHub](https://github.com/jfima/amanu/issues)!
