# Changelog: Reporting System Refactor (2025-12-03)

## Overview
The `amanu report` reporting system has been improved for more efficient analysis of token usage and costs. Reports are now built exclusively based on the working directory (`scribe-work`), providing quick access to statistics without the need to scan user files.

## Key Changes

### 1. Data Source for Reports
- **Before**: `amanu report` scanned both `work` and `results` directories
- **Now**: Reports are built **only** from the `work` directory (default `scribe-work`)
- **Reason**: The `results` directory (`scribe-out`) is user-managed space where files can be modified, moved, or deleted. The `work` directory belongs to the Amanu system and contains a reliable history of completed jobs.

### 2. Smart Work Directory Cleanup

#### Debug Mode (`debug: true`)
When debug mode is enabled:
- All files remain in `scribe-work` after job completion
- Preserved: media files, transcripts, artifacts, metadata
- Useful for analysis and debugging of the processing workflow

#### Production Mode (`debug: false`)
When debug mode is disabled:
- "Heavy" files are automatically removed from `scribe-work` after completion
- **Removed**: `media/`, `transcripts/`, `artifacts/`
- **Preserved**: `_stages/_job.json`, `meta.json`
- Metadata contains all necessary information for reporting

### 3. Metadata Structure for Reporting

For `amanu report` to work correctly, `meta.json` must include:

```json
{
  "job_id": "25-1203-014204_dasha-fima",
  "original_file": "dasha-fima.mp3",
  "created_at": "2025-12-03T01:42:04+03:00",
  "updated_at": "2025-12-03T01:42:27+03:00",
  "configuration": {
    "transcribe": {
      "provider": "whisperx",
      "model": "large-v2"
    },
    "refine": {
      "provider": "gemini",
      "model": "gemini-2.5-flash-lite"
    }
  },
  "processing": {
    "total_tokens": {
      "input": 926,
      "output": 533
    },
    "total_cost_usd": 0.0001,
    "total_time_seconds": 23.45,
    "request_count": 2,
    "stages_completed": ["ingest", "scribe", "refine", "generate", "shelve"]
  }
}
```

### 4. How `amanu report` Works

1. Scans all subdirectories in `paths.work` (default `scribe-work`)
2. For each job, loads `_stages/_job.json` or `meta.json`
3. Extracts statistics:
   - Number of tokens used (input/output)
   - Processing cost in USD
   - Execution time
   - Models used
   - Job completion status
4. Aggregates data for the specified period (default 30 days)
5. Outputs a summary report

### 5. Usage Examples

```bash
# Report for the last 30 days
amanu report

# Report for the last 7 days
amanu report --days 7
```

Example output:
```
==================================================
Amanu Cost & Usage Report (Last 30 days)
==================================================
Total Jobs:        9
Total Cost:        $0.0004
Total Tokens:      7,327
  - Input:         4,364
  - Output:        2,963
Avg Cost/Job:      $0.0000

Jobs by Status:
  - shelve          4
  - refine          3
  - scribe          2

Jobs by Model:
  - large-v2        7
  - large-v3        2
==================================================
```

## Technical Details

### Code Changes

#### `amanu/core/manager.py`
- The `finalize_job()` method now performs "smart cleanup":
  - Copies results to `results` (excluding `_stages`)
  - When `debug=false`, removes heavy files from `work`
  - When `debug=true`, preserves all files in `work`

#### `amanu/core/reporting.py`
- `CostReporter.generate_summary()` now calls `list_jobs(include_history=False)`
- Only the `work` directory is scanned
- Fixed attribute access error for `StageConfig.model`

## Benefits

1. **Performance**: Fast scanning of only the working directory
2. **Reliability**: Data is independent of user actions with output files
3. **Space Savings**: Automatic removal of heavy files in production mode
4. **Flexibility**: Ability to preserve all data for debugging via `debug: true`

## Migration

For existing jobs:
- Jobs in `scribe-work` will be automatically included in reports
- Old jobs in `scribe-out` will not be counted (if statistics are needed, you can temporarily restore `include_history=True` in `reporting.py`)
- It's recommended to periodically clean up old jobs via `amanu jobs cleanup`

## Configuration

In `config.yaml`:
```yaml
debug: false  # Enable smart cleanup
paths:
  work: /home/user/amanu/scribe-work  # Data source for reports
  results: /home/user/amanu/scribe-out  # User-managed space
```
