---
name: Data Science And ML
description: Leakage-safe data preparation, temporal validation, reproducible experiments, and metric comparison rules.
applyTo: ['pipelines/**', 'ml/**', 'notebooks/**', 'src/features/**', 'src/**/features/**']
---

# Data Science And ML

- Use Polars for new tabular pipelines, preferring lazy scans and expression
  APIs. Use DuckDB for local analytical SQL and direct Parquet/CSV exploration.
  Use pandas only at legacy or third-party compatibility boundaries; convert at
  the boundary rather than spreading pandas through new pipeline code.
- Fit transforms, imputers, encoders, selectors, and calibrators only on the
  training partition inside each validation fold.
- Use time-ordered splits for temporal prediction. Never allow future rows,
  labels, aggregates, or availability timestamps into earlier examples.
- Derive the expected sampling interval from the data contract or configuration.
  Where continuity is required, reject gaps larger than one expected interval
  before windowing or resampling.
- Store, compare, join, resample, and engineer features in timezone-aware UTC.
  Convert to local time only in explicit presentation layers.
- Seed every stochastic library from one recorded seed, while documenting
  operations that remain nondeterministic.
- Compare metrics against a named, versioned baseline and report uncertainty or
  variance where it affects the decision.
- Preserve missingness unless an approved transformation handles it. Do not hide
  NaN, infinity, schema drift, or dropped rows through implicit coercion.
- Production logic belongs in importable modules with tests; notebooks may call
  that logic but must not become its only implementation.
- When the optional `experiment-runner` capability is installed, use it for
  experiment artifacts and provenance. Otherwise follow the project's existing
  experiment convention rather than inventing a runner.
