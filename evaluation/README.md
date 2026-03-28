# MemBlocks Evaluation

This folder contains a transparency-driven evaluation harness for MemBlocks.

It is built to evaluate 30-message workloads and produce comparison-ready metrics across multiple method variants.

## What It Tracks

- Per-turn metrics (for each message):
  - turn latency (total, retrieval stage, conversation stage)
  - token usage deltas during that turn
  - process-level token/timing split:
    - `ps1_extraction`
    - `ps2_conflict`
    - `retrieval`
    - `core_memory`
    - `summary`
    - `conversation`
- Full transparency artifacts:
  - retrieval log
  - processing history
  - operation log
  - event stream + event counts
- Aggregated stats for comparison:
  - min / max / avg / p50 / p95 for timings
  - total tokens and tokens-per-turn
  - per-process token totals and average latency
- Optional full-history baseline:
  - runs the main conversation LLM with full chat history every turn
  - reports token deltas and savings versus this baseline
- User-path vs background split:
  - user-path = retrieval + conversation for a single user message turn
  - background = PS1/PS2/core/summary pipeline calls (triggered on flush windows)

## Files

- `evaluation/run_memblocks_evaluation.py`: main evaluation runner
- `evaluation/datasets/default_30_messages.json`: default 30-message dataset
- `evaluation/methods/default_methods.json`: example methods to compare

## Quick Start

From repository root:

```bash
uv run python evaluation/run_memblocks_evaluation.py --enforce-30 --use-reference-task-models
```

This will:

1. Load the 30-message dataset
2. Run each method variant in `default_methods.json`
3. Write a new run directory under `evaluation/runs/run_YYYYMMDD_HHMMSS`

By default, this also runs `full_history_baseline` so you can compare how many
tokens the main LLM would consume if you simply sent the entire chat history
on every turn.

To disable it:

```bash
uv run python evaluation/run_memblocks_evaluation.py --no-full-history-baseline
```

## Rate-Limit Safety

The runner includes built-in delays to avoid model RPM limits:

- `--turn-delay-seconds` (default `3.25`)
- `--method-delay-seconds` (default `8.0`)

For a 20 requests/minute/model limit, `3.25s` per turn keeps the effective
rate under the cap with small buffer.

Example:

```bash
uv run python evaluation/run_memblocks_evaluation.py --enforce-30 --use-reference-task-models --turn-delay-seconds 3.25 --method-delay-seconds 8
```

## Session Window Settings

You can control when background memory pipeline runs fire:

- `--memory-window-limit` (default `20`)
- `--keep-last-n` (default `10`)

With the default 30-message dataset, this causes fewer flush-trigger pipeline runs
than a window size of 10, and gives a cleaner separation between user-path and
background costs.

By default, turn persistence runs in background to match production style:

- `--session-add-background` (default on)
- `--no-session-add-background`

When background mode is on, each "turn" captures user-path cost only, while
pipeline/storage work is tracked separately via background processing metrics.

## Output Structure

Each run folder contains:

- `comparison.csv`: compact table for spreadsheet analysis
- `comparison.md`: human-readable comparison table
- `comparison_summary.json`: full method summaries
- `comparison_rows.json`: flattened comparison rows
- `run_metadata.json`: run metadata
- `messages.json`: messages used in run
- `methods.json`: evaluated methods

Each method subfolder contains:

- `method_report.json`: full per-method report
- `turns.json`: per-message metrics
- `turns.csv`: per-message metrics in tabular format
- `llm_call_type_summary.csv`: process-level token/timing summary
- `llm_records.json`: raw LLM call records
- `retrieval_log.json`: raw retrieval entries
- `processing_history.json`: raw pipeline runs
- `operation_log.json`: raw DB operation log
- `events.json`: raw event stream

If baseline is enabled, run folder also includes:

- `full_history_baseline/` method artifacts with the same key files

## Comparing Additional Methods

Edit `evaluation/methods/default_methods.json` and add new variants by changing:

- `config_overrides` (retrieval flags, top-k, etc.)
- `llm_task_overrides` (provider/model/temperature by task)

Then rerun with:

```bash
uv run python evaluation/run_memblocks_evaluation.py --methods evaluation/methods/default_methods.json --enforce-30
```

## Key Baseline Comparison Columns

In `comparison.csv` and `comparison.md`:

- `vs_full_history_total_token_delta`
- `vs_full_history_total_token_savings_pct`
- `vs_full_history_conversation_token_delta`
- `vs_full_history_conversation_token_savings_pct`

These quantify savings relative to sending full chat history each turn.

## Notes

- This script requires the same infrastructure/services as normal MemBlocks usage (MongoDB, Qdrant, embedding service, and configured LLM keys).
- `evaluation/runs/` is gitignored to keep output artifacts local.
