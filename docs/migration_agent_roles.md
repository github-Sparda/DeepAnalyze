# Agent Role Migration Guide

## Old Node -> New Role Mapping
- understand_files -> DataIngest
- data_quality -> DataQuality
- plan_analysis -> Hypothesis
- parallel_generation -> CodeGen
- execution_guard -> RunGuard
- code_repair -> CodeRepair
- analyze_results -> Insights
- generate_visualizations -> Visualization
- report_outline -> ReportAssembly
- generate_report -> ReportAssembly
- pipeline_guard -> RunGuard
- artifact_validator -> RunGuard

## Artifact Paths
- Old: artifacts/<plan_id>/<kind>/...
- New: artifacts/<plan_id>/<role>/...

## Compatibility
Legacy nodes still run; role mapping is applied in `src/core/agents/registry.py`.
