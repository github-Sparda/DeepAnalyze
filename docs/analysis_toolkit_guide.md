# Analysis Toolkit Guide

This toolkit provides reusable analysis components for runtime agents.

## Usage

```bash
python -m src.core.analytics.toolkit.runner --input data.csv --output-dir outputs/toolkit
```

## Example Config & Script
Example config: `scripts/analysis_toolkit_example_config.json`

```json
{
  "input_path": "data/examples/serum/Normal_EP_serum_data.xlsx",
  "output_dir": "outputs/analysis_toolkit_examples",
  "steps": ["data_profile", "stats_tests", "correlation", "feature_selection", "viz_manhattan_volcano", "viz_heatmap_cluster"]
}
```

Run the minimal end-to-end example (profile -> stats -> visualization):

```bash
conda run -n common python scripts/run_analysis_toolkit_examples.py
```

The script writes `outputs/analysis_toolkit_examples/manifest.json` with `profile/`, `result/`, `plots/` contents for quick inspection.

## Output Structure
- `profile/`: data_profile.json, data_quality.json
- `result/`: stats_results.json, correlation.json, feature_selection.json, normalized.csv
- `plots/`: generated charts (when enabled)
- `summary.json`: pipeline summary

## Theme Configuration
Use `viz_theme.apply_theme` to set font, colors, legend visibility, and sizes.
Default keys:
- `style`, `font_scale`, `palette`, `legend`, `title_size`, `label_size`

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
See `src/core/analytics/toolkit/selector.py`.

## Custom Lines (La)
When no suitable pipeline variant exists, the system can generate a temporary line (La).
Each La is stored with inputs/outputs/quality gates and usage stats under `meta/custom_lines/`.

## Promotion
A scheduled summary aggregates usage stats and produces `line_summary.json` and `promotion_candidates.json`.
Lines with sufficient runs and success rate can be promoted to official registry after review.

## Custom Line Example
Example La definition (stored in meta/custom_lines/lines.json):
```
{
  "line_id": "autogen_123",
  "steps": [
    {"name": "stats_tests", "method": "t_test", "params": {}},
    {"name": "correlation", "method": "pearson", "params": {}}
  ],
  "required_inputs": ["numeric_columns"],
  "required_artifacts": ["stats_results.json", "correlation.json"],
  "quality_gates": ["result:stats_results.json", "result:correlation.json"],
  "compatible_visuals": []
}
```
