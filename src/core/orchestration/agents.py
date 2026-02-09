from __future__ import annotations

import json
from typing import Any, List, Dict, Optional

from .prompts import get_prompt, get_system, render_role_prompt


class HypothesisPlanner:
    def __init__(self, llm: Any, language: str) -> None:
        self.llm = llm
        self.language = language

    def plan(
        self,
        summary: str,
        history: list[str] | None = None,
        plan_id: str | None = None,
        artifact_context: str | None = None,
        telemetry_context: str | None = None,
        goal_hint: str | None = None,
    ) -> str:
        history_text = "\n".join(history or []) or "N_A"
        messages = render_role_prompt(
            "hypothesis_planner",
            self.language,
            prompt_key="hypothesis_planner",
            summary=summary,
            history=history_text,
            plan_id=plan_id or "",
            artifact_context=artifact_context or "",
            telemetry_context=telemetry_context or "",
            goal_hint=goal_hint or "",
        )
        if not messages:
            system = get_system(self.language)
            prompt = get_prompt("hypothesis_planner", self.language)
            messages = [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\nSummary:\n{summary}\n\nHistory:\n{history_text}\n\n"
                        f"Telemetry:\n{telemetry_context or 'N_A'}"
                    ),
                },
            ]
        return self.llm.chat(messages, max_tokens=4096)

    def generate_multiple_hypotheses(self, data_summary: str, num_hypotheses: int = 3) -> List[Dict[str, Any]]:
        """Generate multiple hypotheses with validation steps"""
        prompt = f"""Based on the following data summary, generate {num_hypotheses} distinct analytical hypotheses.
Each hypothesis should include:
1. A clear hypothesis statement
2. Specific validation steps to test the hypothesis
3. Expected artifacts/outcomes
4. Potential insights to discover

Data Summary:
{data_summary}

Return a JSON array with the following structure:
[
  {{
    "title": "Hypothesis title",
    "description": "Detailed hypothesis description",
    "validation_steps": ["step 1", "step 2", "step 3"],
    "expected_artifacts": ["artifact1", "artifact2"],
    "potential_insights": ["insight1", "insight2"]
  }}
]"""
        
        messages = [
            {"role": "system", "content": get_system(self.language)},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.chat(messages, max_tokens=2048)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback to simpler parsing
            return self._parse_hypotheses_fallback(response, num_hypotheses)
    
    def _parse_hypotheses_fallback(self, response: str, num_hypotheses: int) -> List[Dict[str, Any]]:
        """Fallback parsing for hypothesis generation"""
        hypotheses = []
        lines = response.split('\n')
        current_hypothesis = None
        
        for line in lines:
            line = line.strip()
            if line.startswith(('1.', '2.', '3.')) or 'hypothesis' in line.lower():
                if current_hypothesis:
                    hypotheses.append(current_hypothesis)
                current_hypothesis = {
                    "title": line,
                    "description": line,
                    "validation_steps": ["Data exploration", "Statistical analysis", "Visualization"],
                    "expected_artifacts": ["summary_stats", "charts", "insights"],
                    "potential_insights": ["patterns", "correlations", "outliers"]
                }
                if len(hypotheses) >= num_hypotheses:
                    break
        
        if current_hypothesis and len(hypotheses) < num_hypotheses:
            hypotheses.append(current_hypothesis)
        
        # Fill up to required number
        while len(hypotheses) < num_hypotheses:
            hypotheses.append({
                "title": f"Additional Analysis Hypothesis {len(hypotheses) + 1}",
                "description": "Exploratory data analysis to uncover hidden patterns",
                "validation_steps": ["Pattern recognition", "Cluster analysis", "Trend identification"],
                "expected_artifacts": ["cluster_plots", "trend_analysis", "pattern_report"],
                "potential_insights": ["hidden_clusters", "seasonal_patterns", "anomalous_behavior"]
            })
        
        return hypotheses


class CodeGenerator:
    """Agent responsible for generating executable Python code from analysis plans"""
    
    def __init__(self, llm: Any, language: str = "zh") -> None:
        self.llm = llm
        self.language = language
    
    def generate_code(self, analysis_step: str, context: str = "") -> Dict[str, str]:
        """Generate Python code for a specific analysis step"""
        prompt = f"""Generate Python code to accomplish the following analysis step:
{analysis_step}

Context:
{context}

Requirements:
- Use pandas, numpy, matplotlib, seaborn for data analysis
- Include proper error handling
- Add comments explaining each step
- Return results in a structured format
- Save plots to files when applicable

Return a JSON object with:
{{
  "filename": "analysis_step.py",
  "code": "the Python code",
  "description": "brief description of what the code does",
  "dependencies": ["list of required packages"]
}}"""
        
        messages = [
            {"role": "system", "content": "You are an expert Python data scientist."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.chat(messages, max_tokens=2048)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "filename": "analysis.py",
                "code": f"# Analysis for: {analysis_step}\nprint('Implementing: {analysis_step}')",
                "description": analysis_step,
                "dependencies": ["pandas", "numpy"]
            }
    
    def repair_code(self, code: str, error_message: str) -> str:
        """Automatically repair code based on error messages"""
        prompt = f"""The following Python code has an error:

Code:
{code}

Error:
{error_message}

Please fix the code and return only the corrected Python code without any explanations."""
        
        messages = [
            {"role": "system", "content": "You are an expert Python programmer who fixes code errors."},
            {"role": "user", "content": prompt}
        ]
        
        return self.llm.chat(messages, max_tokens=1024)


class VisualizationPlanner:
    """Agent responsible for planning and generating visualizations"""
    
    def __init__(self, llm: Any, language: str = "zh") -> None:
        self.llm = llm
        self.language = language
    
    def plan_visualizations(self, data_description: str, analysis_goals: List[str]) -> List[Dict[str, Any]]:
        """Plan appropriate visualizations based on data and goals"""
        prompt = f"""Based on the following data description and analysis goals, plan appropriate visualizations:

Data Description:
{data_description}

Analysis Goals:
{', '.join(analysis_goals)}

Return a JSON array of visualization plans with:
[
  {{
    "type": "chart type (distribution, correlation, trend, comparison, etc.)",
    "columns": ["column1", "column2"],
    "title": "Chart title",
    "description": "What insight this chart will reveal",
    "library": "matplotlib/seaborn/plotly"
  }}
]"""
        
        messages = [
            {"role": "system", "content": "You are an expert data visualization designer."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.chat(messages, max_tokens=1024)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return self._default_visualization_plans(analysis_goals)
    
    def _default_visualization_plans(self, goals: List[str]) -> List[Dict[str, Any]]:
        """Provide default visualization plans when LLM fails"""
        plans = []
        if goals:
            plans.append({
                "type": "distribution",
                "columns": ["numeric_column"],
                "title": "Data Distribution",
                "description": "Show distribution of key variables",
                "library": "matplotlib"
            })
        return plans


class AnalysisReporter:
    """Agent responsible for generating analysis reports and insights"""
    
    def __init__(self, llm: Any, language: str = "zh") -> None:
        self.llm = llm
        self.language = language
    
    def generate_insights(self, analysis_results: str, data_summary: str) -> str:
        """Generate insights from analysis results"""
        prompt = f"""Based on the following analysis results and data summary, generate key insights:

Data Summary:
{data_summary}

Analysis Results:
{analysis_results}

Please provide:
1. Key findings and patterns discovered
2. Statistical significance of results
3. Business/practical implications
4. Recommendations for further analysis
5. Limitations and caveats"""
        
        messages = [
            {"role": "system", "content": "You are an expert data analyst who translates results into actionable insights."},
            {"role": "user", "content": prompt}
        ]
        
        return self.llm.chat(messages, max_tokens=2048)
    
    def generate_report_outline(self, insights: str, analysis_goals: List[str]) -> str:
        """Generate a structured report outline"""
        prompt = f"""Create a professional report outline based on these insights and goals:

Insights:
{insights}

Original Analysis Goals:
{', '.join(analysis_goals)}

Structure the report with appropriate sections and subsections."""
        
        messages = [
            {"role": "system", "content": "You are an expert technical writer creating data analysis reports."},
            {"role": "user", "content": prompt}
        ]
        
        return self.llm.chat(messages, max_tokens=1024)

# 导出所有类
__all__ = ['HypothesisPlanner', 'CodeGenerator', 'VisualizationPlanner', 'AnalysisReporter']
