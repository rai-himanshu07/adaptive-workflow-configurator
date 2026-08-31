---
name: experiment-runner
description: Scaffold and run a reproducible ML experiment with frozen config, code and data provenance, JSON Lines metrics, and explicit baseline comparison.
argument-hint: '[experiment name] [config path] [data path or version]'
---

# Experiment Runner

Use this workflow for model training, tuning, evaluation, or baseline comparison.

## Scaffold

Identify data with at least one `--data` path or a stable `--data-version` tag:

```bash
python .github/skills/experiment-runner/scripts/scaffold_experiment.py \
  --name forecast-v2 \
  --config configs/forecast-v2.yaml \
  --data data/training.parquet \
  --seed 42
```

Data paths must resolve inside the project root by default. For intentionally
external data, scaffold with `--allow-external-data`, then pass the reviewed
directory as `--allow-data-root PATH` when using `--verify-source-data` during
validate, compare, or register. Source re-hashing is explicit so frequent metric
appends never rescan a large dataset. This also prevents crafted metadata from
making ordinary validation scan arbitrary host paths.

The command creates a unique `artifacts/<run_id>/` atomically. Read
`meta.json:frozen_config` to locate the frozen configuration; do not read the
live source config during the run. `meta.json:provenance_fingerprint` is stable
for the same config, data, seed, code diff, and dependency manifests even though
each run ID remains unique.

## Run Contract

- Seed all supported libraries from `meta.json:seed` and log the effective seed.
- Verify `meta.json` contains a data hash or stable data-version identifier before
  training starts.
- Append metrics through the bundled validator so duplicate keys, malformed
  values, and non-monotonic timestamps cannot silently enter the run:

  ```bash
  python .github/skills/experiment-runner/scripts/experiment_tools.py append \
    --run artifacts/RUN_ID --metric rmse --value 1.42 --split validation \
    --step 1 --sample-count 500 --fold 0
  ```
- Record metric name, value, split or fold, step, timestamp, and relevant sample
  count in each record.
- Keep transforms inside training folds and preserve time order for temporal data.
- Store model outputs, plots, and logs only inside the run directory.

## Baseline And Decision

- Compare against an explicitly supplied baseline run or metrics file. Never
  infer the baseline from the newest artifact.
- Define metric direction and the material-regression threshold in the approved
  experiment plan before running.
- Make aggregation explicit. Example for lower-is-better final-fold means:

  ```bash
  python .github/skills/experiment-runner/scripts/experiment_tools.py compare \
    --candidate artifacts/CANDIDATE --baseline artifacts/BASELINE \
    --metric rmse --split validation --direction lower \
    --aggregation mean-final-folds --max-regression-percent 1
  ```

- The user decides whether a run becomes the accepted baseline. Record that
  decision in `docs/experiments.md`; do not mutate a baseline alias automatically.

## Finish

Validate and register evidence with deterministic commands:

```bash
python .github/skills/experiment-runner/scripts/experiment_tools.py validate \
  --run artifacts/RUN_ID --verify-source-data
python .github/skills/experiment-runner/scripts/experiment_tools.py register \
  --run artifacts/RUN_ID --key-result "rmse=1.42" \
  --baseline BASELINE_RUN_ID --decision candidate
```

Registration is idempotent by run ID. Never commit `artifacts/`; ensure the
target project's ignore and search rules exclude it.
