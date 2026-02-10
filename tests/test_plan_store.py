from __future__ import annotations

import re
import json
from pathlib import Path

from src.core.orchestration.plan_store import PlanStore


def test_plan_store_creates_plan_and_artifacts(tmp_path: Path) -> None:
    store = PlanStore(tmp_path)
    plan_id, plan_dir = store.save_plan(
        "Test plan",
        {"hypotheses": [{"title": "h1", "steps": [], "artifacts": []}]},
        ["h1"],
    )

    assert plan_dir.exists()
    assert (tmp_path / "plans" / plan_id / "analysis_plan.md").exists()
    assert (tmp_path / "plans" / plan_id / "analysis_plan.json").exists()
    assert (tmp_path / "artifacts" / plan_id / "plan" / "analysis_plan.md").exists()
    assert (tmp_path / "artifacts" / plan_id / "plan" / "analysis_plan.json").exists()

    meta_path = tmp_path / "plans" / plan_id / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["plan_id"] == plan_id
    assert isinstance(meta["created_at"], int)
    assert re.match(r"^plan_\d+_[0-9a-f]{8}$", plan_id)
