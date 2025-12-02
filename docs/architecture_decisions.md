# Architecture Decisions

This document records key architectural decisions and the reasoning behind them.

## Refinement Strategy: Text Prompt vs. Audio Cache

**Decision:** For the `refine` stage (analysis, summary, cleanup), we send the generated transcript as **text** within the prompt, rather than asking the model to re-analyze the audio from the cache.

### Context
The pipeline consists of two main stages:
1.  **Scribe:** Transcribes audio to text.
2.  **Refine:** Analyzes the text to produce summaries, action items, and polished content.

Since the audio is already uploaded and cached in the `ingest` stage (especially for Gemini), a valid question arises: *Why not just ask the model to "summarize this audio" using the existing cache, instead of passing the transcript back to it?*

### Reasoning

#### 1. Cost & Efficiency (The "1M vs 15k" Rule)
This is the most critical factor.
*   **Audio Processing:** 1 hour of audio is equivalent to roughly **1,000,000 tokens** for the model to process. Even with caching, the "compute" cost and latency of analyzing this volume of data are significant.
*   **Text Processing:** That same hour of audio, when converted to a text transcript, is typically only **10,000 - 15,000 tokens**.
*   **Impact:** Sending the text is approximately **60x cheaper and faster** than asking the model to re-scan the full audio context.

#### 2. Precision & Determinism
*   **Text:** When we send the transcript, we force the model to analyze *exactly* what was written. We have a deterministic baseline.
*   **Audio:** If we ask the model to analyze the audio again, it is a probabilistic process. It might "hear" slightly different things, focus on different parts, or hallucinate details that were not present in the generated transcript. This creates a disconnect between the "raw transcript" file and the "summary" file.

#### 3. Session Independence
The `scribe` and `refine` stages run in separate sessions to ensure modularity and fault tolerance. The model does not "remember" the text it generated in the previous session.
*   If we used audio, the model would have to re-generate the internal understanding of the speech from scratch.
*   By passing the text, we provide the "state" explicitly, allowing the `refine` stage to be stateless and idempotent.

### Trade-offs

**Cons of Text-in-Prompt:**
*   **Log Size:** Sending the full transcript in the prompt makes debug logs very large. (Mitigated by log truncation).
*   **Context Window:** The transcript counts towards the context window limit (though 15k tokens is negligible compared to the 1M+ capacity of modern models like Gemini 1.5 Pro).

**Pros of Audio Cache (Rejected):**
*   **"Zero" Data Transfer:** No need to send the text string.
*   **Tone Analysis:** The model could theoretically analyze emotion/tone better from audio. (However, for standard summaries, text is sufficient).

### Conclusion
We prioritize **cost, speed, and consistency**. Therefore, the `refine` stage will always operate on the *text output* of the `scribe` stage, not the raw audio.