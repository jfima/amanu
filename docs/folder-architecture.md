# New Amanu Folder Architecture

## 📁 Structure

```
aivoice/
├── scribe-in/              # 📥 Input folder (like AirDrop)
│   └── recording.mp3       # File appears here
│                          # ⚠️ Deleted immediately after copying to scribe-work
│
├── scribe-work/            # 🔧 Work folder (active and failed jobs)
│   ├── 20251124_152420_REC00057/  # ❌ Failed job (kept for 7 days)
│   │   ├── state.json              # {"status": "failed", ...}
│   │   ├── meta.json
│   │   ├── audio/
│   │   │   └── original.mp3        # Original saved here
│   │   ├── transcripts/
│   │   └── _stages/
│   │
│   └── 20251124_163000_REC00058/  # ⏳ In progress
│       └── ...
│
└── scribe-out/             # ✅ Output folder (successful results only)
    └── 2025/11/24/
        └── 20251124_152420_REC00057/
            ├── meta.json
            ├── audio/
            │   └── original.mp3
            └── transcripts/
                ├── raw.json
                └── clean.md
```

## 🔄 Workflow

### Watch Mode

```
1. 📥 File appears → scribe-in/recording.mp3
2. 🔧 Job created → scribe-work/20251124_165546_recording/
3. 📋 Copied → scribe-work/.../audio/original.mp3
4. 🗑️ Deleted → scribe-in/recording.mp3 (original is safe)
5. ⚙️ Pipeline: scout → prep → scribe → refine → shelve
6. ✅ Success → scribe-out/2025/11/24/20251124_165546_recording/
7. ❌ Error → remains in scribe-work/ (7 days)
```

### Error Handling

- **Error at any stage**: job remains in `scribe-work/` with `failed` status
- **Retention**: 7 days (configurable in `config.yaml`)
- **Recovery**: `amanu jobs retry <job_id> --from-stage <stage>`
- **Auto-cleanup**: old failed jobs are deleted automatically

## ⚙️ Configuration

```yaml
paths:
  input: "./scribe-in"       # Input folder
  work: "./scribe-work"      # Work folder
  results: "./scribe-out"    # Output folder

cleanup:
  failed_jobs_retention_days: 7      # Failed jobs retention
  completed_jobs_retention_days: 1   # Retention in work after move to scribe-out
  auto_cleanup_enabled: true         # Auto-cleanup on start
```

## 📝 CLI Commands

```bash
# Start watch mode
amanu watch

# View jobs
amanu jobs list                    # All jobs
amanu jobs list --status failed    # Failed only
amanu jobs show <job_id>           # Job details

# Retry failed job
amanu jobs retry <job_id>
amanu jobs retry <job_id> --from-stage scribe

# Cleanup
amanu jobs cleanup --older-than 7d --status failed
```
