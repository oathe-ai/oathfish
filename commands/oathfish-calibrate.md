---
name: oathfish-calibrate
description: "Record prediction outcomes and view calibration data for OathFish runs. Tracks Brier scores, domain bias, acquiescence rates, and prepares ForecastBench submissions."
argument-hint: '--record-outcome RUN_ID prediction_id outcome OR --report OR --forecastbench'
disable-model-invocation: true
---

OathFish Calibration Management: $ARGUMENTS

## Operations

### Record Outcome
`/oathfish-calibrate --record-outcome RUN_ID prediction_id true|false`
Records the resolved outcome for a specific prediction. Calls MCP
calibration_record_outcome().

### View Calibration Report
`/oathfish-calibrate --report`
Displays current calibration data: Brier scores (raw + corrected), domain
bias analysis, acquiescence rates, holdout validation results.
Calls MCP calibration_get_ensemble_metrics().

### Prepare ForecastBench Submission
`/oathfish-calibrate --forecastbench`
Prepares predictions in ForecastBench submission format.
