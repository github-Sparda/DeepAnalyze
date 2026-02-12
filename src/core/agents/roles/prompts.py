from __future__ import annotations

SYSTEM_BASE = {
    "en": (
        "You are DeepAnalyze Orchestrator. Follow instructions precisely. "
        "Output must be concise, structured, and actionable."
    ),
    "zh": "你是 DeepAnalyze 编排器。严格遵循指令，输出应简洁、结构化、可执行。",
}

PROMPTS = {
    "file_summary": {
        "en": (
            "Summarize the dataset files provided. Identify formats, likely schemas, "
            "and any obvious analysis directions. Keep under 15 bullets."
        ),
        "zh": "总结数据文件，识别格式、可能的字段与分析方向，控制在15条以内。",
    },
    "planning": {
        "en": (
            "Based on the file summary, propose multiple hypotheses and an analysis plan. "
            "Return Markdown with: 1) hypotheses list, 2) steps per hypothesis, "
            "3) expected artifacts (tables/plots)."
        ),
        "zh": (
            "基于文件摘要提出多个可验证假设与分析计划。返回 Markdown，包含："
            "1）假设列表；2）每个假设的步骤；3）预期产物（表/图）。"
        ),
    },
    "hypothesis_planner": {
        "en": (
            "Generate multiple testable hypotheses and an analysis plan with closure requirements. "
            "Return Markdown with: 1) hypotheses list, 2) steps per hypothesis, "
            "3) expected artifacts (tables/plots), 4) success criteria, 5) follow-up action, "
            "6) two validation paths per hypothesis (A/B) with different method families."
        ),
        "zh": (
            "生成多个可验证假设与分析计划（闭环要求）。返回 Markdown，包含："
            "1）假设列表；2）每个假设的步骤；3）预期产物（表/图）；"
            "4）成功判据；5）后续行动建议；6）每个假设必须给出 A/B 两条方法学不同的验证路径。"
        ),
    },
    "planning_struct": {
        "en": (
            "Convert the plan to strict JSON. "
            "Schema: {hypotheses:[{id,title,hypothesis,validation_plan_steps,expected_artifacts,validation_paths:[{path_id,method_family,steps,expected_artifacts}]}]}. "
            "Rules: id must be H1/H2...; keep original wording; "
            "validation_plan_steps must be ordered strings; expected_artifacts must be concrete filenames or chart names; "
            "validation_paths must contain at least 2 entries and method_family must differ."
        ),
        "zh": (
            "将计划转换为严格 JSON。"
            "格式：{hypotheses:[{id,title,hypothesis,validation_plan_steps,expected_artifacts,"
            "validation_paths:[{path_id,method_family,steps,expected_artifacts}]}]}。"
            "规则：id 必须是 H1/H2...；尽量保留原始表述；"
            "validation_plan_steps 为有序字符串数组；expected_artifacts 为具体文件名或图表名；"
            "validation_paths 至少包含两条路径且 method_family 必须不同。"
        ),
    },
    "codegen": {
        "en": (
            "Generate Python analysis steps based on the plan. Output strict JSON with keys: "
            "steps: [{name, filename, code}]. Each code must be runnable standalone. "
            "Use pandas and standard libs. Prefer calling analytics toolkit helpers and core visualization renderer when available. "
            "Ensure each step writes explicit artifacts for validation."
        ),
        "zh": (
            "根据计划生成 Python 脚本。输出严格 JSON，键为 steps: [{name, filename, code}]。"
            "每段代码可独立运行，优先使用 pandas 与标准库。可用时优先调用 analytics toolkit 工具与统一渲染层。"
            "每个步骤必须产出可验证的明确产物（json/csv/图）。"
        ),
    },
    "code_fix": {
        "en": (
            "Fix the Python code based on the error output. "
            "Return only the corrected code, no markdown."
        ),
        "zh": "根据错误输出修复代码，仅返回修复后的代码，不要 Markdown。",
    },
    "analysis": {
        "en": (
            "Analyze the execution outputs and result files. Summarize key findings, "
            "and reference any generated figures/tables."
        ),
        "zh": "分析执行输出与结果文件，总结关键发现并引用生成的图表/表格。",
    },
    "analysis_structured": {
        "en": (
            "Analyze execution outputs and return strict JSON with keys: "
            "summary, key_findings, evidence, limitations, next_steps. "
            "Ensure every hypothesis has a validation status and conclusion."
        ),
        "zh": (
            "分析执行输出并返回严格 JSON，字段包含：summary、key_findings、"
            "evidence、limitations、next_steps。"
            "确保每条假设都有验证状态与结论。"
        ),
    },
    "hypothesis_refine": {
        "en": "Propose new hypotheses to verify based on the analysis results.",
        "zh": "基于分析结果提出新的可验证假设。",
    },
    "report_outline": {
        "en": "Draft a report outline based on analysis results. Use numbered sections.",
        "zh": "基于分析结果撰写报告大纲，使用编号章节。",
    },
    "report": {
        "en": (
            "Write the final report based on the outline and analysis results. "
            "Use the specified language, format, and export mode preferences. "
            "If export mode is academic_redraw, favor formal academic structure and "
            "high-quality figure descriptions. If export mode is html_print, keep layout "
            "close to the HTML presentation."
        ),
        "zh": (
            "基于大纲与分析结果撰写最终报告。遵循指定语言、格式与导出模式。"
            "若导出模式为 academic_redraw，使用更学术的结构并详细描述图表；"
            "若为 html_print，则保持接近 HTML 的排版。"
        ),
    },
    "report_structured": {
        "en": (
            "Return strict JSON with keys: title, summary, sections "
            "(list of {title, body}), highlights, limitations. "
            "Sections MUST include hypothesis->validation->conclusion->next steps."
        ),
        "zh": (
            "返回严格 JSON，字段包含：title、summary、sections（{title, body} 列表）、"
            "highlights、limitations。"
            "各章节必须包含假设→验证→结论→后续。"
        ),
    },
    "data_quality": {
        "en": "Summarize data quality issues and key profiling results.",
        "zh": "总结数据质量问题与关键概况结果。",
    },
}

ROLE_TEMPLATES = {
    "file_understanding": {
        "system": "{system}",
        "user": "{prompt}\n\nFiles:\n{file_info}",
    },
    "planning": {
        "system": "{system}",
        "user": (
            "{prompt}\n\nSummary:\n{summary}\n\nPlan ID: {plan_id}\n{artifact_context}\n"
            "Telemetry:\n{telemetry_context}"
        ),
    },
    "hypothesis_planner": {
        "system": "{system}",
        "user": (
            "{prompt}\n\nSummary:\n{summary}\n\nHistory:\n{history}\n\nPlan ID: {plan_id}\n"
            "{artifact_context}\nTelemetry:\n{telemetry_context}\nGoal hints:\n{goal_hint}"
        ),
    },
    "codegen": {
        "system": "{system}",
        "user": (
            "{prompt}\n\nPlan:\n{plan}\n\nPlan ID: {plan_id}\n{artifact_context}\n"
            "Telemetry:\n{telemetry_context}"
        ),
    },
    "analysis": {
        "system": "{system}",
        "user": (
            "{prompt}\n\nOutputs:\n{outputs}\n\nPlan ID: {plan_id}\n{artifact_context}\n"
            "Telemetry:\n{telemetry_context}"
        ),
    },
    "report_outline": {
        "system": "{system}",
        "user": (
            "{prompt}\n\nAnalysis:\n{analysis}\n\nPlan ID: {plan_id}\n{artifact_context}\n"
            "Telemetry:\n{telemetry_context}"
        ),
    },
    "report": {
        "system": "{system}",
        "user": (
            "{prompt}\n\nLanguage: {language}\nFormat: {format}\nExport mode: {mode}\n"
            "Outline:\n{outline}\n\nAnalysis:\n{analysis}\n\nPlan ID: {plan_id}\n"
            "{artifact_context}\nTelemetry:\n{telemetry_context}"
        ),
    },
}


def get_prompt(key: str, language: str) -> str:
    return PROMPTS.get(key, {}).get(language) or PROMPTS.get(key, {}).get("en", "")


def get_system(language: str) -> str:
    return SYSTEM_BASE.get(language) or SYSTEM_BASE["en"]


def render_role_prompt(role: str, language: str, **kwargs) -> list[dict[str, str]]:
    template = ROLE_TEMPLATES.get(role)
    if not template:
        return []
    system = get_system(language)
    prompt = get_prompt(kwargs.get("prompt_key", ""), language)
    payload = {
        "system": system,
        "prompt": prompt,
        "language": language,
        "plan_id": kwargs.get("plan_id", ""),
        "artifact_context": kwargs.get("artifact_context", ""),
        "history": kwargs.get("history", ""),
        "telemetry_context": kwargs.get("telemetry_context", ""),
        **kwargs,
    }
    return [
        {"role": "system", "content": template["system"].format(**payload)},
        {"role": "user", "content": template["user"].format(**payload)},
    ]
