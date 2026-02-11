# Analysis Toolkit Guide

This toolkit provides reusable analysis components for runtime agents.

## Usage

```bash
python -m src.core.tools.analysis_toolkit.runner --input data.csv --output-dir outputs/toolkit
```

## Output Structure
- `profile/`: data_profile.json, data_quality.json
- `result/`: stats_results.json, correlation.json, feature_selection.json, normalized.csv
- `plots/`: generated charts (when enabled)
- `summary.json`: pipeline summary

## Theme Configuration
Use `viz_theme.apply_theme` to set font, colors, legend visibility, and sizes.

## Notes
Some advanced modules are stubs and will be implemented in follow-up iterations.

## Pipeline Registry
Pipelines define multiple executable variants with compatible method combinations.

Example: key_feature_screening
- Variant t_test_volcano: t-test + FDR + variance selection + volcano
- Variant anova_manhattan: ANOVA + FDR + effect size + manhattan

Each variant declares compatible visuals to avoid invalid combinations.

## Pipeline Selection
To avoid long LLM context, use rule-based selection to shortlist pipelines based on data profile.
See `src/core/tools/analysis_toolkit/selector.py`.

## Custom Lines (La)
When no suitable pipeline variant exists, the system can generate a temporary line (La).
Each La is stored with inputs/outputs/quality gates and usage stats under `meta/custom_lines/`.

## Promotion
A scheduled summary aggregates usage stats and produces `line_summary.json` and `promotion_candidates.json`.
Lines with sufficient runs and success rate can be promoted to official registry after review.
