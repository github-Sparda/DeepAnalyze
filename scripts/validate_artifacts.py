from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_json(path: Path) -> list[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def validate_registry(data/sessions/active_dir: Path) -> dict[str, object]:
    artifacts_dir = data/sessions/active_dir / "artifacts"
    summary: dict[str, object] = {"plans": [], "errors": []}
    if not artifacts_dir.exists():
        summary["errors"].append("artifacts directory missing")
        return summary

    for plan_dir in sorted(artifacts_dir.iterdir()):
        if not plan_dir.is_dir():
            continue
        registry_path = plan_dir / "registry.json"
        if not registry_path.exists():
            summary["errors"].append(f"registry missing: {plan_dir.name}")
            continue
        entries = _load_json(registry_path)
        counts: dict[str, int] = {}
        entry_errors: list[str] = []
        for entry in entries:
            plan_id = entry.get("plan_id")
            kind = entry.get("kind", "unknown")
            counts[kind] = counts.get(kind, 0) + 1
            if not plan_id:
                entry_errors.append(f"missing plan_id in {registry_path}")
            elif plan_id != plan_dir.name:
                entry_errors.append(f"plan_id mismatch in {registry_path}: {plan_id}")
            path = entry.get("path")
            if path and not Path(path).exists():
                entry_errors.append(f"missing path: {path}")
        summary["plans"].append(
            {
                "plan_id": plan_dir.name,
                "entries": len(entries),
                "counts": counts,
                "errors": entry_errors,
            }
        )
        summary["errors"].extend(entry_errors)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate artifact registry entries.")
    parser.add_argument("--data/sessions/active", default="data/sessions/active", help="Workspace directory")
    args = parser.parse_args()
    data/sessions/active_dir = Path(args.data/sessions/active)
    summary = validate_registry(data/sessions/active_dir)
    output_dir = data/sessions/active_dir / "outputs/logs" / "artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "summary.json"
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Artifact summary written to {output_path}")


if __name__ == "__main__":
    main()
