# Pipeline Dependencies and Error Handling

## Overview

This document describes the dependency system between pipeline stages and the error handling mechanisms in Amanu.

## Stage Dependencies

| Stage | Prerequisites | Error Messages |
|-------|---------------|----------------|
| ingest | Source file exists | "Source file not found: {path}" |
| scribe | ingest completed | "Cannot run 'scribe' stage: ingest result not found" |
| refine | scribe OR ingest | "Cannot run 'refine' stage: no input data found" |
| generate | refine completed | "Cannot run 'generate' stage: enriched context not found" |
| shelve | generate completed | "Cannot run 'shelve' stage: no documents found" |

## Validation Logic

### IngestStage
- Validates that the source audio file exists
- Checks that the file is not empty
- Error: `FileNotFoundError` or `ValueError` with descriptive message

### ScribeStage
- Validates that ingest stage completed successfully
- Checks for `ingest_result` in JobObject or fallback to file system
- Error: `ValueError` with hint to run ingest first

### RefineStage
- Validates that either:
  1. A valid transcript file exists (standard mode)
  2. Valid ingest data exists (direct mode)
- Additional check for direct mode: warns if language is not specified
- Error: `ValueError` with detailed missing files information

### GenerateStage
- Validates that refine stage completed successfully
- Checks for `enriched_context_file` existence
- Error: `ValueError` with hint to run refine first

### ShelveStage
- Validates that generate stage completed successfully
- Checks for `final_document_files` or scans for artifacts
- Error: `ValueError` with hint to run generate first

## Common Error Scenarios

### Running refine without prerequisites
```
Error: Cannot run 'refine' stage: no input data found.
Solution: Either run 'scribe' stage first (transcript mode) or ensure 'ingest' stage completed (direct mode).
Missing files:
  - Transcript: /path/to/transcripts/raw_transcript.json
  - Ingest result: Missing
```

### Running scribe without ingest
```
Error: Cannot run 'scribe' stage: ingest result not found.
Hint: Try running 'amanu ingest <filename>' first
```

### Running generate without refine
```
Error: Cannot run 'generate' stage: enriched context not found.
Hint: Try running 'amanu refine <filename>' first
```

### Running shelve without generate
```
Error: Cannot run 'shelve' stage: no documents found.
Hint: Try running 'amanu generate <filename>' first
```

### Language not specified for direct mode
```
Warning: Language not specified for direct audio analysis.
Recommendation: Consider setting language in configuration or running 'scribe' stage first.
```

## Implementation Details

### BaseStage.validate_prerequisites()
Each stage implements this abstract method to perform its specific validation logic. The method is called automatically before `execute()` in the `run()` method.

### Error Handling in CLI
The CLI provides contextual hints based on error patterns:
- Detects missing dependencies
- Suggests appropriate commands to fix the issue
- Provides clear next steps for users

## Testing Scenarios

### Test Case 1: Direct Mode Without Language
```bash
amanu ingest REC00002_2.mp3
amanu refine REC00002_2.mp3
# Expected: Warning about language, but successful execution
```

### Test Case 2: Refine Without Any Prerequisites
```bash
amanu refine REC00002_2.mp3
# Expected: Error with clear message about missing input data
```

### Test Case 3: Complete Pipeline
```bash
amanu run REC00002_2.mp3
# Expected: Successful execution through all stages
```

## Benefits

1. **Early Detection**: Errors are caught before expensive API calls
2. **Clear Messages**: Users get actionable information about what's missing
3. **Prevention**: Prevents similar errors in the codebase
4. **Consistency**: Unified validation approach across all stages

## Future Improvements

- Add configuration validation
- Add API key availability checks
- Implement dry-run mode for validation only
- Add more detailed dependency tracking