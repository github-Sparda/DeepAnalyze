#!/usr/bin/env python3
"""
Enhanced Hypothesis Planner - 集成LLM的假设生成器
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime

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
            "data_quality": "良好" if data_summary.get('missing_values', 0) == 0 else "需要注意"
        }
        return characteristics
    
    def generate_hypotheses_with_llm(self, data_characteristics: Dict[str, Any], data_sample: str = "") -> List[Dict[str, Any]]:
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
        except:
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
                    "expected_outcome": ""
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
                "expected_outcome": "发现强相关或弱相关的变量对"
            })
            
            hypotheses.append({
                "description": "数据可能呈现某种分布模式",
                "validation_method": "绘制直方图，进行正态性检验",
                "expected_outcome": "识别数据分布类型（正态、偏态等）"
            })
        
        if categorical_count > 0:
            hypotheses.append({
                "description": "分类变量间可能存在关联",
                "validation_method": "进行卡方检验，创建交叉表",
                "expected_outcome": "发现显著相关的分类组合"
            })
        
        if numeric_count > 0 and categorical_count > 0:
            hypotheses.append({
                "description": "不同类别间的数值变量可能存在差异",
                "validation_method": "进行t检验或ANOVA分析",
                "expected_outcome": "识别在不同类别间有显著差异的数值变量"
            })
        
        # 添加通用假设
        hypotheses.append({
            "description": "数据中可能存在异常值或离群点",
            "validation_method": "计算箱线图统计量，识别超出3倍标准差的点",
            "expected_outcome": "定位潜在的数据质量问题或有趣的现象"
        })
        
        return hypotheses
    
    def create_analysis_plan(self, data_summary: Dict[str, Any], data_sample: str = "") -> Dict[str, Any]:
        """创建完整的分析计划"""
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
            "created_at": datetime.now().isoformat()
        }
        
        return plan_record
    
    def _generate_validation_steps(self, hypotheses: List[Dict[str, Any]], data_summary: Dict[str, Any]) -> List[str]:
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
                steps.append(f"{i}. 验证假设: {hypothesis.get('description', '')}")
        
        return steps
    
    def _generate_expected_outputs(self, hypotheses: List[Dict[str, Any]]) -> List[str]:
        """生成预期输出"""
        outputs = [
            "数据质量报告",
            "描述性统计摘要",
            "数据分布可视化图表",
            "相关性分析结果"
        ]
        
        for hypothesis in hypotheses:
            desc = hypothesis.get('description', '')
            if '相关' in desc:
                outputs.append("变量相关性热力图")
            elif '分布' in desc:
                outputs.append("分布直方图和密度图")
            elif '分类' in desc:
                outputs.append("分类变量交叉表")
            elif '差异' in desc:
                outputs.append("组间比较箱线图")
        
        return list(set(outputs))  # 去重

# 使用示例和测试
if __name__ == "__main__":
    # 测试假设规划器
    planner = EnhancedHypothesisPlanner()
    
    # 模拟数据摘要
    test_data_summary = {
        "data_source": "serum_data.xlsx",
        "rows": 1783,
        "columns": 56,
        "numeric_columns": 54,
        "categorical_columns": 2,
        "missing_values": 0
    }
    
    # 创建分析计划
    plan = planner.create_analysis_plan(test_data_summary)
    
    print("生成的分析计划:")
    print(json.dumps(plan, indent=2, ensure_ascii=False))