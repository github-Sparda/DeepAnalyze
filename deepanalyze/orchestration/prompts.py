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
            "Generate multiple testable hypotheses and an analysis plan. "
            "Return Markdown with: 1) hypotheses list, 2) steps per hypothesis, "
            "3) expected artifacts (tables/plots)."
        ),
        "zh": (
            "生成多个可验证假设与分析计划。返回 Markdown，包含："
            "1）假设列表；2）每个假设的步骤；3）预期产物（表/图）。"
        ),
    },
    "planning_struct": {
        "en": (
            "Convert the plan to JSON with keys: hypotheses: [{title, steps, artifacts}]."
        ),
        "zh": "将计划转换为 JSON，包含 hypotheses: [{title, steps, artifacts}]。",
    },
    "codegen": {
        "en": (
            "Generate Python analysis steps based on the plan. Output strict JSON with keys: "
            "steps: [{name, filename, code}]. Each code must be runnable standalone. "
            "Use pandas and standard libs."
        ),
        "zh": (
            "根据计划生成 Python 脚本。输出严格 JSON，键为 steps: [{name, filename, code}]。"
            "每段代码可独立运行，优先使用 pandas 与标准库。"
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
        "user": "{prompt}\n\nSummary:\n{summary}\n\nPlan ID: {plan_id}\n{artifact_context}",
    },
    "hypothesis_planner": {
        "system": "{system}",
        "user": "{prompt}\n\nSummary:\n{summary}\n\nHistory:\n{history}\n\nPlan ID: {plan_id}\n{artifact_context}",
    },
    "codegen": {
        "system": "{system}",
        "user": "{prompt}\n\nPlan:\n{plan}\n\nPlan ID: {plan_id}\n{artifact_context}",
    },
    "analysis": {
        "system": "{system}",
        "user": "{prompt}\n\nOutputs:\n{outputs}\n\nPlan ID: {plan_id}\n{artifact_context}",
    },
    "report_outline": {
        "system": "{system}",
        "user": "{prompt}\n\nAnalysis:\n{analysis}\n\nPlan ID: {plan_id}\n{artifact_context}",
    },
    "report": {
        "system": "{system}",
        "user": "{prompt}\n\nLanguage: {language}\nFormat: {format}\nExport mode: {mode}\n"
        "Outline:\n{outline}\n\nAnalysis:\n{analysis}\n\nPlan ID: {plan_id}\n{artifact_context}",
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
        "plan_id": kwargs.get("plan_id", ""),
        "artifact_context": kwargs.get("artifact_context", ""),
        "history": kwargs.get("history", ""),
        **kwargs,
    }
    return [
        {"role": "system", "content": template["system"].format(**payload)},
        {"role": "user", "content": template["user"].format(**payload)},
    ]
