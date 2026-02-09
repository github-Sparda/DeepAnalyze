<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/docs/specs/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/docs/specs/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'docs/specs update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Codex Project Guidance

These instructions supplement OpenSpec and apply to all Codex work in this repo.

## Project Context
- Primary codebase is Python (DeepAnalyze core in `src/core/`, src/api in `src/api/`).
- Demos live under `demo/` (WebUI, JupyterUI, CLI).
- Examples and case studies live under `data/examples/`.

## Programming Guidelines
- Prefer small, focused changes that align with existing module structure and naming.
- Keep public interfaces stable; document any behavioral changes in OpenSpec proposals first.
- Avoid introducing new dependencies without a clear need and a short rationale.
- Use Python conventions (snake_case, type hints where already used) and keep code readable.

## Testing and Validation
- No top-level test runner is documented; if you add or change behavior, include a short manual verification plan in the proposal/tasks (CLI/src/api/UI steps as relevant).
- If you add tests, keep them minimal and targeted; do not introduce new frameworks unless necessary.

## Git / PR Expectations
- Keep commits scoped and descriptive; avoid mixing unrelated changes.
- Note any required model weights or datasets in the PR description if changes depend on them.
- For UI/demo changes, include a brief run/usage note.

## Documentation
- Update `README.md` or relevant docs/guides if you add or change user-facing behavior.
- For new demos or data/exampless, follow the existing folder structure and add a concise README.
