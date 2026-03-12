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


class EnhancedHypothesisPlanner:
    """增强版假设规划器，集成LLM能力"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.session_manager = None

    def set_session_manager(self, session_manager):
        """设置会话管理器"""
        self.session_manager = session_manager

    def analyze_data_characteristics(self, data_summary: Dict[str, Any]) -> Dict[str, Any]:
        """分析数据特征以指导假设生成"""
        characteristics = {
            "data_shape": f"{data_summary.get('rows', 0)}行 × {data_summary.get('columns', 0)}列",
            "numeric_variables": data_summary.get('numeric_columns', 0),
            "categorical_variables": data_summary.get('categorical_columns', 0),
            "missing_values": data_summary.get('missing_values', 0),
            "data_quality": "良好" if data_summary.get('missing_values', 0) == 0 else "需要注意",
        }
        return characteristics

    def generate_hypotheses_with_llm(
        self,
        data_characteristics: Dict[str, Any],
        data_sample: str = "",
    ) -> List[Dict[str, Any]]:
        """使用LLM生成假设"""
        if not self.llm_client:
            # 如果没有LLM客户端，使用预设假设
            return self._generate_default_hypotheses(data_characteristics)

        try:
            prompt = self._build_hypothesis_prompt(data_characteristics, data_sample)
            response = self.llm_client.chat([{"role": "user", "content": prompt}])

            # 解析LLM响应
            hypotheses = self._parse_llm_response(response)
            return hypotheses

        except Exception as e:
            print(f"LLM假设生成失败: {e}")
            return self._generate_default_hypotheses(data_characteristics)

    def _build_hypothesis_prompt(self, data_characteristics: Dict[str, Any], data_sample: str) -> str:
        """构建假设生成提示"""
        prompt = f"""基于以下数据特征，生成3-5个合理的数据分析假设：

数据特征：
{json.dumps(data_characteristics, indent=2, ensure_ascii=False)}

数据样本：
{data_sample[:500] if data_sample else "无样本数据"}

请按照以下格式生成假设：
1. 假设描述 - 可能的数据模式或关系
2. 验证方法 - 如何验证这个假设
3. 预期结果 - 如果假设成立会看到什么

请用JSON格式返回，包含hypotheses数组，每个假设包含description、validation_method、expected_outcome字段。
"""
        return prompt

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """解析LLM响应"""
        try:
            # 尝试提取JSON部分
            import re

            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if 'hypotheses' in data:
                    return data['hypotheses']
        except Exception:
            pass

        # 如果解析失败，返回基本格式
        return self._extract_hypotheses_from_text(response)

    def _extract_hypotheses_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取假设"""
        lines = text.split('\n')
        hypotheses = []
        current_hypothesis = {}

        for line in lines:
            line = line.strip()
            if line.startswith(('1.', '2.', '3.', '4.', '5.')):
                if current_hypothesis:
                    hypotheses.append(current_hypothesis)
                current_hypothesis = {
                    "description": line.split('.', 1)[1].strip(),
                    "validation_method": "",
                    "expected_outcome": "",
                }
            elif '验证' in line or '方法' in line:
                if current_hypothesis:
                    current_hypothesis["validation_method"] = line
            elif '预期' in line or '结果' in line:
                if current_hypothesis:
                    current_hypothesis["expected_outcome"] = line

        if current_hypothesis:
            hypotheses.append(current_hypothesis)

        return hypotheses[:5]  # 限制最多5个假设

    def _generate_default_hypotheses(self, data_characteristics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成默认假设（当LLM不可用时）"""
        numeric_count = data_characteristics.get('numeric_variables', 0)
        categorical_count = data_characteristics.get('categorical_variables', 0)

        hypotheses = []

        if numeric_count > 0:
            hypotheses.append({
                "description": "数值变量之间可能存在相关性",
                "validation_method": "计算相关系数矩阵，绘制散点图",
                "expected_outcome": "发现强相关或弱相关的变量对",
            })

            hypotheses.append({
                "description": "数据可能呈现某种分布模式",
                "validation_method": "绘制直方图，进行正态性检验",
                "expected_outcome": "识别数据分布类型（正态、偏态等）",
            })

        if categorical_count > 0:
            hypotheses.append({
                "description": "分类变量间可能存在关联",
                "validation_method": "进行卡方检验，创建交叉表",
                "expected_outcome": "发现显著相关的分类组合",
            })

        if numeric_count > 0 and categorical_count > 0:
            hypotheses.append({
                "description": "不同类别间的数值变量可能存在差异",
                "validation_method": "进行t检验或ANOVA分析",
                "expected_outcome": "识别在不同类别间有显著差异的数值变量",
            })

        # 添加通用假设
        hypotheses.append({
            "description": "数据中可能存在异常值或离群点",
            "validation_method": "计算箱线图统计量，识别超出3倍标准差的点",
            "expected_outcome": "定位潜在的数据质量问题或有趣的现象",
        })

        return hypotheses

    def create_analysis_plan(self, data_summary: Dict[str, Any], data_sample: str = "") -> Dict[str, Any]:
        """创建完整的分析计划"""
        from datetime import datetime

        # 分析数据特征
        characteristics = self.analyze_data_characteristics(data_summary)

        # 生成假设
        hypotheses = self.generate_hypotheses_with_llm(characteristics, data_sample)

        # 准备验证步骤
        validation_steps = self._generate_validation_steps(hypotheses, data_summary)

        # 创建计划记录
        plan_record = {
            "datasource": data_summary.get('data_source', 'unknown'),
            "data_characteristics": characteristics,
            "hypothesis_list": hypotheses,
            "validation_steps": validation_steps,
            "expected_outputs": self._generate_expected_outputs(hypotheses),
            "created_at": datetime.now().isoformat(),
        }

        return plan_record

    def _generate_validation_steps(
        self,
        hypotheses: List[Dict[str, Any]],
        data_summary: Dict[str, Any],
    ) -> List[str]:
        """生成验证步骤"""
        steps = []
        numeric_vars = data_summary.get('numeric_columns', 0)
        categorical_vars = data_summary.get('categorical_columns', 0)

        # 基础数据质量检查
        steps.append("1. 执行数据质量检查（缺失值、重复值、异常值）")
        steps.append("2. 生成描述性统计摘要")

        # 根据假设生成特定步骤
        for i, hypothesis in enumerate(hypotheses, 3):
            method = hypothesis.get('validation_method', '')
            if '相关' in method and numeric_vars > 1:
                steps.append(f"{i}. 计算变量间相关性矩阵")
            elif '分布' in method and numeric_vars > 0:
                steps.append(f"{i}. 绘制数值变量分布图")
            elif '分类' in method and categorical_vars > 1:
                steps.append(f"{i}. 分析分类变量间关联性")
            elif '差异' in method and numeric_vars > 0 and categorical_vars > 0:
                steps.append(f"{i}. 比较不同类别间的数值差异")
            else:
                steps.append(f"{i}. 执行假设验证: {hypothesis.get('description', '')}")

        return steps

    def _generate_expected_outputs(self, hypotheses: List[Dict[str, Any]]) -> List[str]:
        outputs = ["data_quality_report", "descriptive_statistics"]
        for hypothesis in hypotheses:
            expected = hypothesis.get('expected_outcome', '')
            if expected:
                outputs.append(expected)
        return outputs
    
    def generate_report_outline(self, insights: str, analysis_goals: List[str]) -> str:
        """Generate a structured report outline"""
        if not self.llm_client:
            return "## 分析报告大纲\n\n### 核心发现\n### 方法说明\n### 结论与建议"
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
        
        return self.llm_client.chat(messages, max_tokens=1024)

# 导出所有类
__all__ = ['HypothesisPlanner', 'CodeGenerator', 'VisualizationPlanner', 'AnalysisReporter']
