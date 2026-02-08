"""
Enhanced Intent Recognition System for DeepAnalyze
基于关键词匹配的实用意图识别系统
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import re
from collections import defaultdict


class EnhancedChatIntent(Enum):
    """增强版聊天意图分类"""
    CHAT_ONLY = "chat_only"                    # 一般聊天
    REUSE_ARTIFACT = "reuse_artifact"          # 复用已有结果
    GUIDED_ANALYSIS = "guided_analysis"        # 指导式分析
    EXPLORATORY_ANALYSIS = "exploratory_analysis"  # 探索性分析
    DATA_INQUIRY = "data_inquiry"              # 数据查询
    MODEL_QUESTION = "model_question"          # 模型相关问题
    TECHNICAL_SUPPORT = "technical_support"    # 技术支持
    FEEDBACK_COMPLAINT = "feedback_complaint"  # 反馈投诉


@dataclass
class EnhancedRouterDecision:
    """增强版路由决策"""
    intent: EnhancedChatIntent
    confidence: float                      # 置信度 (0-1)
    goal: Optional[str] = None
    artifact_preview: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    detected_entities: Optional[Dict[str, List[str]]] = None  # 识别的实体


class IntentRecognizer:
    """智能意图识别器"""
    
    def __init__(self):
        # 简化的关键词词典
        self.guided_keywords = [
            'analyze', '分析', '研究', '调查', 'trend', '趋势', '走势',
            'compare', '对比', '比较', 'correlation', '相关性', '关联',
            'insight', '洞察', '见解', '发现', 'focus', '聚焦',
            'evaluate', '评估', '评价', 'statistics', '统计'
        ]
        
        self.exploratory_keywords = [
            'explore', '探索', '发现', 'suggest', '建议', '推荐',
            'auto', '自动', '自动化', 'generate', '生成', 'create',
            'find', '寻找', '查找', 'open-ended', '开放式', 'survey', '调研'
        ]
        
        self.reuse_keywords = [
            'show', '显示', '展示', 'display', 'review', '回顾', '查看',
            'report', '报告', 'result', '结果', 'chart', '图表',
            'visual', '可视化', 'plot', '绘图', 'again', '再次', '重新'
        ]
        
        self.inquiry_keywords = [
            'data', '数据', 'dataset', '表格', 'column', '列', 'field', '字段',
            'row', '行', 'record', '记录', 'size', '大小', 'count', '数量',
            'info', '信息', 'information', '详情'
        ]
        
        self.support_keywords = [
            'error', '错误', 'bug', '问题', 'help', '帮助', 'support', '支持',
            'how to', '如何', '怎样', '怎么', 'install', '安装', 'setup', '配置',
            'troubleshoot', '故障排除', 'debug', '调试'
        ]
        
        self.feedback_keywords = [
            'bad', '差', '不好', 'worst', 'slow', '慢', '卡顿', 'lag',
            'wrong', '错误', 'incorrect', '不准', 'complaint', '投诉', '不满',
            'improve', '改进', '优化', 'better'
        ]
    
    def _calculate_confidence(self, matches: int, total_keywords: int, message_length: int) -> float:
        """计算置信度"""
        if matches == 0:
            return 0.1  # 最低置信度
        
        # 基础置信度基于匹配比例（放宽条件）
        base_confidence = min(1.0, matches / max(1, total_keywords * 0.3))  # 从0.5改为0.3
        
        # 根据消息长度调整（太短的消息置信度较低）
        length_factor = min(1.0, message_length / 10.0)  # 从15改为10
        
        # 综合置信度
        confidence = base_confidence * length_factor
        
        # 确保在合理范围内
        return max(0.1, min(0.95, confidence))
    
    def _extract_entities(self, message: str) -> Dict[str, List[str]]:
        """提取消息中的关键实体"""
        entities = defaultdict(list)
        
        # 提取文件名
        file_pattern = r'([\w\-]+\.csv|[\w\-]+\.xlsx?|[\w\-]+\.json)'
        files = re.findall(file_pattern, message, re.IGNORECASE)
        if files:
            entities['files'].extend(files)
        
        # 提取数字
        numbers = re.findall(r'\d+(?:\.\d+)?', message)
        if numbers:
            entities['numbers'].extend(numbers)
        
        # 提取列名（简单的英文单词）
        column_pattern = r'(?:column|列|字段)\s+([a-zA-Z_][\w]*)'
        columns = re.findall(column_pattern, message, re.IGNORECASE)
        if columns:
            entities['columns'].extend(columns)
        
        return dict(entities)
    
    def classify_intent(
        self, 
        message: str, 
        manifest: Optional[Dict[str, Any]] = None
    ) -> EnhancedRouterDecision:
        """
        智能意图分类
        
        Args:
            message: 用户消息
            manifest: 工作区元数据
            
        Returns:
            增强版路由决策
        """
        # 对于中文，保持原文；对于英文，转换为小写
        text = message.strip()
        message_length = len(text)
        
        # 提取实体
        entities = self._extract_entities(message)
        
        # 检查是否有可用的工件
        artifact = None
        if manifest:
            from .intent_router import _choose_artifact
            artifact = _choose_artifact(manifest)
        
        # 计算各类意图的匹配分数
        intent_scores = {}
        
        # 复用意图检查（只有当有工件时才考虑）
        if artifact:
            reuse_matches = sum(1 for keyword in self.reuse_keywords 
                              if keyword in text)
            intent_scores[EnhancedChatIntent.REUSE_ARTIFACT] = {
                'matches': reuse_matches,
                'confidence': self._calculate_confidence(reuse_matches, len(self.reuse_keywords), message_length)
            }
        
        # 指导式分析检查
        guided_matches = sum(1 for keyword in self.guided_keywords 
                           if keyword in text)
        intent_scores[EnhancedChatIntent.GUIDED_ANALYSIS] = {
            'matches': guided_matches,
            'confidence': self._calculate_confidence(guided_matches, len(self.guided_keywords), message_length)
        }
        
        # 探索性分析检查
        exploratory_matches = sum(1 for keyword in self.exploratory_keywords 
                                if keyword in text)
        intent_scores[EnhancedChatIntent.EXPLORATORY_ANALYSIS] = {
            'matches': exploratory_matches,
            'confidence': self._calculate_confidence(exploratory_matches, len(self.exploratory_keywords), message_length)
        }
        
        # 数据查询检查
        inquiry_matches = sum(1 for keyword in self.inquiry_keywords 
                            if keyword in text)
        intent_scores[EnhancedChatIntent.DATA_INQUIRY] = {
            'matches': inquiry_matches,
            'confidence': self._calculate_confidence(inquiry_matches, len(self.inquiry_keywords), message_length)
        }
        
        # 技术支持检查
        support_matches = sum(1 for keyword in self.support_keywords 
                            if keyword in text)
        intent_scores[EnhancedChatIntent.TECHNICAL_SUPPORT] = {
            'matches': support_matches,
            'confidence': self._calculate_confidence(support_matches, len(self.support_keywords), message_length)
        }
        
        # 反馈投诉检查
        feedback_matches = sum(1 for keyword in self.feedback_keywords 
                             if keyword in text)
        intent_scores[EnhancedChatIntent.FEEDBACK_COMPLAINT] = {
            'matches': feedback_matches,
            'confidence': self._calculate_confidence(feedback_matches, len(self.feedback_keywords), message_length)
        }
        
        # 选择最高置信度的意图
        best_intent = max(intent_scores.items(), key=lambda x: x[1]['confidence'])
        intent, score_info = best_intent
        
        # 特殊处理：如果置信度都很低，则默认为一般聊天
        if score_info['confidence'] < 0.25:  # 从0.3降到0.25
            return EnhancedRouterDecision(
                intent=EnhancedChatIntent.CHAT_ONLY,
                confidence=0.9,
                reason="low_confidence_default"
            )
        
        # 构造返回结果
        decision_kwargs = {
            'intent': intent,
            'confidence': score_info['confidence'],
            'detected_entities': entities,
            'reason': f"matched_{score_info['matches']}_keywords"
        }
        
        # 根据意图类型添加特定信息
        if intent == EnhancedChatIntent.REUSE_ARTIFACT and artifact:
            decision_kwargs['artifact_preview'] = artifact
        elif intent in [EnhancedChatIntent.GUIDED_ANALYSIS, EnhancedChatIntent.DATA_INQUIRY]:
            decision_kwargs['goal'] = message.strip()
        
        return EnhancedRouterDecision(**decision_kwargs)


# 全局实例
intent_recognizer = IntentRecognizer()


def get_intent_recognizer() -> IntentRecognizer:
    """获取全局意图识别器实例"""
    return intent_recognizer


def enhanced_classify_intent(
    message: str, 
    manifest: Optional[Dict[str, Any]] = None
) -> EnhancedRouterDecision:
    """
    便捷函数：使用增强意图识别器进行分类
    
    Args:
        message: 用户消息
        manifest: 工作区元数据
        
    Returns:
        增强版路由决策
    """
    recognizer = get_intent_recognizer()
    return recognizer.classify_intent(message, manifest)