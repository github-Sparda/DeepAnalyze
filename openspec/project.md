# Project Context

## Purpose
DeepAnalyze is an agentic LLM system for autonomous data science, covering end-to-end workflows (data prep, analysis, modeling, visualization, and report generation) and open-ended data research across structured, semi-structured, and unstructured sources.

## Tech Stack
- Python 3.12 (primary runtime)
- PyTorch, Transformers, vLLM (model inference/serving)
- FastAPI, Uvicorn, WebSockets (OpenAI-style API server)
- NumPy, pandas, scikit-learn, matplotlib, seaborn (data science stack)
- Node.js + npm (WebUI demo in `demo/chat`)
- Jupyter Lab integration for JupyterUI demo

## Project Conventions

### Code Style
No top-level formatter is specified. Follow existing module structure and naming in `deepanalyze/` and `API/`. Keep Python conventions (snake_case, type hints where already used).

### Architecture Patterns
- Core Python package in `deepanalyze/` for model usage and tooling.
- OpenAI-style API server under `API/`.
- Demos and UIs under `demo/` (WebUI, JupyterUI, CLI).
- Training/evaluation frameworks vendored under `deepanalyze/ms-swift/` and `deepanalyze/SkyRL/`.
- Example case studies under `example/`.

### Testing Strategy
Not explicitly documented. When adding features, include targeted tests where feasible and/or provide manual run steps (CLI/API/UI) in the change proposal tasks.

### Git Workflow
Direct PRs are accepted; contribution guidelines focus on code/model/UI improvements and case studies. No branching or commit conventions are specified at the top level.

## Domain Context
- Target users run DeepAnalyze as a data analyst/agent on local data and expect a report-style output.
- Supports heterogeneous inputs (CSV/Excel/DB/JSON/XML/YAML/TXT/Markdown) and produces analyst-grade reports.
- OpenAI-style API endpoints are part of the public interface.

## Important Constraints
- Model weights and large datasets are external (HuggingFace); keep code changes independent of local weights.
- Inference and training environments are recommended to be separated to avoid dependency conflicts.

## External Dependencies
- HuggingFace model and dataset hosting (DeepAnalyze-8B, DataScience-Instruct-500K).
- vLLM serving runtime.
- FastAPI/OpenAI-style API clients.
