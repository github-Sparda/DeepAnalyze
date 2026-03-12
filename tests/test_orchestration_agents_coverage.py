from __future__ import annotations

from types import SimpleNamespace

import src.core.orchestration.agents as agents


class _FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, max_tokens=None):
        self.calls.append((messages, max_tokens))
        return self.responses.pop(0)


def test_hypothesis_planner_and_fallback_parsers(monkeypatch):
    llm = _FakeLLM([
        '[{"title":"plan-response"}]',
        '[{"title":"A","description":"D","validation_steps":["s"],"expected_artifacts":["a"],"potential_insights":["i"]}]',
    ])
    planner = agents.HypothesisPlanner(llm, "zh")
    monkeypatch.setattr(agents, "render_role_prompt", lambda *a, **k: [])
    monkeypatch.setattr(agents, "get_system", lambda lang: "sys")
    monkeypatch.setattr(agents, "get_prompt", lambda key, lang: "prompt")
    text = planner.plan("summary", history=["h1"])
    assert text.startswith("[")
    generated = planner.generate_multiple_hypotheses("summary", num_hypotheses=1)
    assert generated[0]["title"] == "A"

    llm2 = _FakeLLM(["1. hypothesis one\nvalidation method\nexpected result"])
    planner2 = agents.HypothesisPlanner(llm2, "zh")
    fallback = planner2.generate_multiple_hypotheses("summary", num_hypotheses=2)
    assert len(fallback) == 2


def test_code_visualization_and_reporter_agents():
    llm = _FakeLLM([
        '{"filename":"x.py","code":"print(1)","description":"d","dependencies":["pandas"]}',
        "fixed-code",
        '[{"type":"distribution","columns":["x"],"title":"T","description":"D","library":"matplotlib"}]',
        "insights",
    ])
    codegen = agents.CodeGenerator(llm)
    result = codegen.generate_code("step", "ctx")
    assert result["filename"] == "x.py"
    assert codegen.repair_code("bad", "err") == "fixed-code"

    viz = agents.VisualizationPlanner(llm)
    plan = viz.plan_visualizations("data", ["goal"])
    assert plan[0]["type"] == "distribution"

    reporter = agents.AnalysisReporter(llm)
    assert reporter.generate_insights("res", "summary") == "insights"

    llm_bad = _FakeLLM(["not-json", "not-json"])
    assert agents.CodeGenerator(llm_bad).generate_code("step")["filename"] == "analysis.py"
    assert agents.VisualizationPlanner(llm_bad).plan_visualizations("data", ["goal"])[0]["library"] == "matplotlib"


def test_enhanced_hypothesis_planner_paths():
    planner = agents.EnhancedHypothesisPlanner()
    planner.set_session_manager(object())
    characteristics = planner.analyze_data_characteristics({"rows": 10, "columns": 3, "numeric_columns": 2, "categorical_columns": 1, "missing_values": 0})
    defaults = planner.generate_hypotheses_with_llm(characteristics)
    assert defaults

    llm = _FakeLLM(['{"hypotheses":[{"description":"d","validation_method":"m","expected_outcome":"e"}]}'])
    planner2 = agents.EnhancedHypothesisPlanner(llm_client=llm)
    generated = planner2.generate_hypotheses_with_llm(characteristics, "sample")
    assert generated[0]["description"] == "d"

    llm_bad = _FakeLLM(["1. 假设一\n验证方法：相关分析\n预期结果：存在关联"])
    planner3 = agents.EnhancedHypothesisPlanner(llm_client=llm_bad)
    extracted = planner3.generate_hypotheses_with_llm(characteristics, "sample")
    assert extracted[0]["description"]

    plan = planner3.create_analysis_plan(
        {"rows": 5, "columns": 2, "numeric_columns": 2, "categorical_columns": 1, "missing_values": 1, "data_source": "demo"},
        "sample",
    )
    assert plan["datasource"] == "demo"
    assert plan["validation_steps"]
    assert plan["expected_outputs"]
    assert "JSON格式" in planner3._build_hypothesis_prompt(characteristics, "abc")
    llm_outline = _FakeLLM(["outline"])
    planner4 = agents.EnhancedHypothesisPlanner(llm_client=llm_outline)
    assert planner4.generate_report_outline("insights", ["goal"]) == "outline"
    assert agents.EnhancedHypothesisPlanner().generate_report_outline("insights", ["goal"]).startswith("## 分析报告大纲")
