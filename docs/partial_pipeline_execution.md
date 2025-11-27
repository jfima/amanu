# Partial Pipeline Execution Walkthrough

We have implemented a flexible way to control the execution flow of the Amanu pipeline using a single, consistent parameter: `--stop-after`.

## New Capabilities

### 1. Start and Stop (`amanu run`)

You can now start a new job and stop it at a specific stage without finalizing it (it remains in `scribe-work`).

```bash
# Run Ingest and Scribe, then stop
amanu run input/dasha-fima.mp3 --stop-after scribe
```

**Result:**
- `ingest` stage runs
- `scribe` stage runs
- Pipeline stops
- Job remains in `scribe-work/{job_id}`

### 2. Continue and Stop (`amanu <stage>`)

You can continue an existing job (automatically selected if not provided) up to a specific stage.

```bash
# Continue the last incomplete job up to Refine
amanu scribe --stop-after refine
```

**Result:**
- `scribe` stage runs (if not already done)
- `refine` stage runs
- Pipeline stops
- Job remains in `scribe-work/{job_id}`

### 3. Continue to Completion

If you run a stage command without `--stop-after`, it will now attempt to complete the pipeline from that stage onwards (unless you stop it again).

```bash
# Continue from Scribe to the end (Finalize)
amanu scribe
```

**Result:**
- `scribe` runs
- `refine` runs
- `generate` runs
- `shelve` runs
- Job is finalized to `scribe-out/`

### 4. Re-running Stages

To re-run a stage (e.g. for debugging), simply run the command again.

```bash
# Re-run Scribe on the last job (even if completed)
amanu scribe --stop-after scribe
```

**Result:**
- Finds the last job (regardless of completion status)
- Resets scribe status to PENDING
- Runs scribe again
- Stops after scribe

## Command Reference

| Command | Argument | Description |
| :--- | :--- | :--- |
| `amanu run` | `--stop-after <stage>` | Run new job up to stage |
| `amanu scribe` | `--stop-after <stage>` | Execute scribe (and subsequent stages) |
| `amanu refine` | `--stop-after <stage>` | Execute refine (and subsequent stages) |
| `amanu shelve` | `--stop-after <stage>` | Execute shelve (and subsequent stages) |

**Available Stages:** `ingest`, `scribe`, `refine`, `generate`, `shelve`

## Testing Logic

### Implementation Details

**Core Components:**

1. **`JobManager.get_ready_jobs(stage)`**:
   - Returns jobs where **previous** stages are completed
   - **Ignores** completion status of the target stage
   - Allows re-execution of completed stages

2. **`cli.py` Command Handlers**:
   - `amanu scribe` → Finds job → Calls `retry_job(from_stage=SCRIBE)` → Executes pipeline
   - Always resets target stage and subsequent stages to PENDING
   - Respects `--stop-after` parameter

3. **`Pipeline.run_all_stages(job_id, stop_after)`**:
   - Executes stages sequentially
   - Stops after specified stage if `stop_after` is set
   - Does NOT finalize job if stopped early

### Expected Behaviors

**Scenario 1: First-time execution**
```bash
amanu run input/test.mp3 --stop-after scribe
```
- Creates new job
- Runs: ingest → scribe
- Stops after scribe
- Job remains in `scribe-work/`

**Scenario 2: Re-execution (debugging)**
```bash
amanu scribe --stop-after scribe
```
- Finds last job (even if scribe is COMPLETED)
- Resets scribe, refine, generate, shelve to PENDING
- Runs: scribe
- Stops after scribe

**Scenario 3: Continuation**
```bash
amanu scribe --stop-after refine
```
- Finds last job
- Resets scribe, refine, generate, shelve to PENDING
- Runs: scribe → refine
- Stops after refine

**Scenario 4: Full pipeline**
```bash
amanu scribe
```
- Finds last job
- Resets scribe, refine, generate, shelve to PENDING
- Runs: scribe → refine → generate → shelve
- Finalizes job to `scribe-out/`

### Manual Testing Checklist

- [ ] **Fresh run**: `amanu run input/test.mp3 --stop-after ingest`
  - Verify: ingest COMPLETED, others PENDING
  
- [ ] **First scribe**: `amanu scribe --stop-after scribe`
  - Verify: scribe COMPLETED, ingest unchanged
  
- [ ] **Re-run scribe**: `amanu scribe --stop-after scribe`
  - Verify: scribe runs again, outputs updated
  
- [ ] **Continue to refine**: `amanu scribe --stop-after refine`
  - Verify: scribe + refine COMPLETED
  
- [ ] **Complete pipeline**: `amanu scribe`
  - Verify: all stages run, job finalized to `scribe-out/`
