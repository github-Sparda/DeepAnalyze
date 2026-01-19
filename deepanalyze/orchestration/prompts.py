SYSTEM_BASE = (
    "You are DeepAnalyze Orchestrator. Follow instructions precisely. "
    "Output must be concise and actionable."
)

FILE_SUMMARY_PROMPT = (
    "Summarize the dataset files provided. Identify formats, likely schemas, "
    "and any obvious analysis directions. Keep under 15 bullets."
)

PLANNING_PROMPT = (
    "Based on the file summary, propose multiple hypotheses and an analysis plan. "
    "Return Markdown with: 1) hypotheses list, 2) steps per hypothesis, "
    "3) expected artifacts (tables/plots)."
)

CODEGEN_PROMPT = (
    "Generate Python analysis steps based on the plan. Output strict JSON with keys: "
    "steps: [{name, filename, code}]. Each code must be runnable standalone. "
    "Use pandas and standard libs."
)

CODE_FIX_PROMPT = (
    "Fix the Python code based on the error output. "
    "Return only the corrected code, no markdown."
)

ANALYSIS_PROMPT = (
    "Analyze the execution outputs and result files. Summarize key findings, "
    "and reference any generated figures/tables."
)

REPORT_OUTLINE_PROMPT = (
    "Draft a report outline based on analysis results. Use numbered sections." 
)

REPORT_PROMPT = (
    "Write the final report based on the outline and analysis results. "
    "Use the specified language, format, and export mode preferences. "
    "If export mode is academic_redraw, favor formal academic structure and "
    "high-quality figure descriptions. If export mode is html_print, keep layout "
    "close to the HTML presentation."
)
