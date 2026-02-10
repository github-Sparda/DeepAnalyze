"""
Enhanced AI Assistant Core Engine
增强版AI助手核心对话引擎
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from .context_manager import (
    ContextManager, 
    ContextMode, 
    MemoryType, 
    get_ai_assistant,
    process_user_message
)
from ..error.handler import ErrorHandler, ErrorSeverity, ErrorCategory
from ..state.manager import get_session_state, update_session_state

# 延迟导入API客户端以避免循环依赖
def get_api_client():
    # 暂时返回None，避免API依赖
    return None


class ResponseStyle(Enum):
    """响应风格"""
    ANALYTICAL = "analytical"     # 分析型
    CONVERSATIONAL = "conversational"  # 对话型
    TECHNICAL = "technical"       # 技术型
    EXECUTIVE = "executive"       # 执行型


class IntentType(Enum):
    """意图类型"""
    DATA_ANALYSIS = "data_docs_analysis"      # 数据分析
    CODE_GENERATION = "code_generation"   # 代码生成
    VISUALIZATION = "visualization"      # 可视化
    REPORT_GENERATION = "report_generation"  # 报告生成
    GENERAL_CHAT = "general_chat"        # 一般聊天
    HELP_REQUEST = "help_request"        # 帮助请求
    FILE_MANAGEMENT = "file_management"   # 文件管理


@dataclass
class AnalysisRequest:
    """分析请求"""
    intent: IntentType
    query: str
    data_files: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # 1-5, 5为最高优先级


@dataclass
class ResponseTemplate:
    """响应模板"""
    style: ResponseStyle
    structure: List[str]  # 响应结构要点
    tone_indicators: List[str]  # 语气指示词
    data_examples_patterns: List[str]  # 示例模式


class AIAssistantEngine:
    """AI助手核心引擎"""
    
    def __init__(self):
        self.context_manager = ContextManager()
        self.error_handler = ErrorHandler()
        # 延迟初始化API客户端
        self._api_client = None
        self.response_templates = self._initialize_templates()
    
    @property
    def api_client(self):
        if self._api_client is None:
            self._api_client = get_api_client()
        return self._api_client
    
    def _initialize_templates(self) -> Dict[IntentType, ResponseTemplate]:
        """初始化响应模板"""
        return {
            IntentType.DATA_ANALYSIS: ResponseTemplate(
                style=ResponseStyle.ANALYTICAL,
                structure=["问题理解", "方法建议", "实施步骤", "预期结果"],
                tone_indicators=["建议", "可以", "推荐", "分析显示"],
                data_examples_patterns =["基于您的数据", "我建议", "分析结果表明"]
            ),
            IntentType.CODE_GENERATION: ResponseTemplate(
                style=ResponseStyle.TECHNICAL,
                structure=["代码目的", "实现逻辑", "关键参数", "使用说明"],
                tone_indicators=["以下是", "代码如下", "实现方式"],
                data_examples_patterns =["```python", "这段代码", "函数作用是"]
            ),
            IntentType.VISUALIZATION: ResponseTemplate(
                style=ResponseStyle.ANALYTICAL,
                structure=["图表类型建议", "数据要求", "实现方法", "解读要点"],
                tone_indicators=["适合用", "建议绘制", "可以展示"],
                data_examples_patterns =["推荐使用", "这种图表", "能够清晰显示"]
            ),
            IntentType.REPORT_GENERATION: ResponseTemplate(
                style=ResponseStyle.EXECUTIVE,
                structure=["报告结构", "核心发现", "数据支撑", "行动建议"],
                tone_indicators=["综上所述", "数据显示", "建议采取"],
                data_examples_patterns =["报告包含", "主要发现", "基于分析"]
            ),
            IntentType.GENERAL_CHAT: ResponseTemplate(
                style=ResponseStyle.CONVERSATIONAL,
                structure=["理解回应", "相关信息", "进一步建议"],
                tone_indicators=["明白", "了解", "好的"],
                data_examples_patterns =["我理解", "关于这个", "您可以"]
            ),
            IntentType.HELP_REQUEST: ResponseTemplate(
                style=ResponseStyle.CONVERSATIONAL,
                structure=["问题确认", "解决方案", "操作步骤", "注意事项"],
                tone_indicators=["可以这样", "建议您", "需要注意"],
                data_examples_patterns =["您的意思是", "解决方法是", "操作步骤"]
            )
        }
    
    def process_message(
        self,
        session_id: str,
        user_message: str,
        context_mode: ContextMode = ContextMode.HYBRID,
        style_preference: Optional[ResponseStyle] = None
    ) -> Dict[str, Any]:
        """处理用户消息的主入口"""
        try:
            # 1. 意图识别
            intent = self._classify_intent(user_message)
            
            # 2. 上下文管理
            context_messages = self.context_manager.get_context_messages(
                session_id,
                max_tokens=6000,  # 为响应留出空间
                include_system_prompt=True
            )
            
            # 3. 构建完整提示
            full_prompt = self._build_enhanced_prompt(
                user_message, 
                context_messages, 
                intent,
                style_preference
            )
            
            # 4. 调用LLM生成响应
            response_content = self._generate_llm_response(full_prompt, session_id)
            
            # 5. 后处理响应
            processed_response = self._post_process_response(
                response_content, 
                intent, 
                session_id
            )
            
            # 6. 更新上下文和记忆
            self._update_context_and_memory(
                session_id, 
                user_message, 
                processed_response,
                intent
            )
            
            return {
                "content": processed_response,
                "intent": intent.value,
                "confidence": self._calculate_confidence(intent, user_message),
                "context_used": len(context_messages),
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.EXECUTION,
                context={"session_id": session_id, "message_length": len(user_message)}
            )
            return self._get_fallback_response(str(e))
    
    def _classify_intent(self, message: str) -> IntentType:
        """意图分类"""
        message_lower = message.lower()
        
        # 数据分析相关
        if any(keyword in message_lower for keyword in [
            '分析', '统计', '趋势', '相关性', '回归', '聚类',
            'analyze', 'statistic', 'trend', 'correlation', 'regression'
        ]):
            return IntentType.DATA_ANALYSIS
        
        # 代码生成相关
        elif any(keyword in message_lower for keyword in [
            '代码', '编程', 'python', 'script', '函数', '算法',
            'code', 'program', 'script', 'function', 'algorithm'
        ]):
            return IntentType.CODE_GENERATION
        
        # 可视化相关
        elif any(keyword in message_lower for keyword in [
            '图表', '可视化', '绘图', '图形', 'plot', 'chart', 'graph',
            '可视化', '图', '表格'
        ]):
            return IntentType.VISUALIZATION
        
        # 报告生成相关
        elif any(keyword in message_lower for keyword in [
            '报告', '文档', '总结', '结论', '建议', 'recommendation',
            'report', 'document', 'summary', 'conclusion', 'suggestion'
        ]):
            return IntentType.REPORT_GENERATION
        
        # 帮助请求相关
        elif any(keyword in message_lower for keyword in [
            '怎么', '如何', '帮助', '教程', '指导', 'help', 'how to'
        ]):
            return IntentType.HELP_REQUEST
        
        # 文件管理相关
        elif any(keyword in message_lower for keyword in [
            '文件', '上传', '下载', '数据', 'dataset', 'file', 'upload'
        ]):
            return IntentType.FILE_MANAGEMENT
        
        # 默认为一般聊天
        else:
            return IntentType.GENERAL_CHAT
    
    def _build_enhanced_prompt(
        self,
        user_message: str,
        context_messages: List[Dict[str, Any]],
        intent: IntentType,
        style_preference: Optional[ResponseStyle] = None
    ) -> List[Dict[str, Any]]:
        """构建增强版提示"""
        template = self.response_templates.get(intent, self.response_templates[IntentType.GENERAL_CHAT])
        style = style_preference or template.style
        
        # 系统提示
        system_prompt = self._get_system_prompt(intent, style)
        
        # 上下文消息
        prompt_messages = [system_prompt] if system_prompt else []
        prompt_messages.extend(context_messages)
        
        # 当前用户消息
        user_prompt = self._format_user_message(user_message, intent, template)
        prompt_messages.append(user_prompt)
        
        return prompt_messages
    
    def _get_system_prompt(self, intent: IntentType, style: ResponseStyle) -> Optional[Dict[str, str]]:
        """获取系统提示"""
        system_prompts = {
            (IntentType.DATA_ANALYSIS, ResponseStyle.ANALYTICAL): (
                "你是专业的数据分析顾问。请提供详细的分析方法、统计技术建议和实施步骤。"
                "使用专业术语，给出具体的数据处理建议。"
            ),
            (IntentType.CODE_GENERATION, ResponseStyle.TECHNICAL): (
                "你是经验丰富的Python数据科学家。请生成高效、可读性强的代码。"
                "包含必要的注释和错误处理，遵循最佳实践。"
            ),
            (IntentType.VISUALIZATION, ResponseStyle.ANALYTICAL): (
                "你是数据可视化专家。请推荐最适合的图表类型和实现方法。"
                "解释选择理由和最佳实践。"
            ),
            (IntentType.REPORT_GENERATION, ResponseStyle.EXECUTIVE): (
                "你是商业分析师。请生成结构清晰、见解深刻的分析报告。"
                "重点突出关键发现和可行建议。"
            ),
            (IntentType.HELP_REQUEST, ResponseStyle.CONVERSATIONAL): (
                "你是友好的技术助手。请用通俗易懂的语言解释问题并提供清晰的指导。"
            )
        }
        
        prompt = system_prompts.get((intent, style))
        if not prompt:
            # 默认通用提示
            prompt = "你是一个智能数据分析助手，请提供准确、有用的回答。"
        
        return {"role": "system", "content": prompt}
    
    def _format_user_message(
        self, 
        message: str, 
        intent: IntentType, 
        template: ResponseTemplate
    ) -> Dict[str, str]:
        """格式化用户消息"""
        # 添加上下文信息
        enhanced_message = f"# 用户请求\n{message}\n\n"
        
        # 根据意图添加特定提示
        intent_prompts = {
            IntentType.DATA_ANALYSIS: "请分析数据并提供详细的统计见解。",
            IntentType.CODE_GENERATION: "请生成完整、可运行的Python代码。",
            IntentType.VISUALIZATION: "请推荐合适的可视化方法和实现代码。",
            IntentType.REPORT_GENERATION: "请生成结构化的分析报告大纲。"
        }
        
        if intent in intent_prompts:
            enhanced_message += f"# 特殊要求\n{intent_prompts[intent]}\n\n"
        
        return {"role": "user", "content": enhanced_message}
    
    def _generate_llm_response(self, prompt: List[Dict[str, Any]], session_id: str) -> str:
        """调用LLM生成响应"""
        try:
            # 使用统一API客户端
            response = self.api_client.chat_completion(
                messages=prompt,
                model="default",
                temperature=0.7,
                max_tokens=2000
            )
            
            if isinstance(response, str):
                return response
            elif isinstance(response, dict) and 'content' in response:
                return response['content']
            else:
                return str(response)
                
        except Exception as e:
            # 回退到模拟响应
            return self._get_simulated_response(prompt[-1]['content'])
    
    def _get_simulated_response(self, user_message: str) -> str:
        """获取模拟响应（当API不可用时）"""
        message_lower = user_message.lower()
        
        if '分析' in message_lower:
            return (
                "我理解您想要进行数据分析。基于您的请求，我建议采用以下步骤：\n\n"
                "1. **数据探索**：首先检查数据质量、缺失值和基本统计信息\n"
                "2. **数据清洗**：处理异常值和缺失数据\n"
                "3. **统计分析**：进行描述性统计和推断性分析\n"
                "4. **可视化**：创建图表展示关键发现\n"
                "5. **洞察总结**：提炼业务价值和行动建议\n\n"
                "请上传您的数据文件，我将为您执行完整的分析流程。"
            )
        elif '代码' in message_lower:
            return (
                "我可以帮您生成Python数据分析代码。以下是一个通用的数据分析模板：\n\n"
                "```python\n"
                "import pandas as pd\n"
                "import numpy as np\n"
                "import matplotlib.pyplot as plt\n"
                "import seaborn as sns\n\n"
                "# 读取数据\ndata = pd.read_csv('your_data.csv')\n\n"
                "# 基本信息\nprint(data.info())\nprint(data.describe())\n\n"
                "# 可视化\nplt.figure(figsize=(10, 6))\nsns.histplot(data['column_name'])\n"
                "plt.title('数据分布')\nplt.show()\n```\n\n"
                "请告诉我您具体想要分析什么，我可以提供更有针对性的代码。"
            )
        else:
            return (
                "感谢您的消息！我是您的数据分析AI助手。\n\n"
                "我可以帮助您：\n"
                "📊 进行数据分析和统计建模\n"
                "💻 生成Python分析代码\n"
                "📈 创建数据可视化图表\n"
                "📄 生成专业的分析报告\n"
                "📁 管理和处理数据文件\n\n"
                "请告诉我您想要做什么，我会为您提供专业的帮助！"
            )
    
    def _post_process_response(self, response: str, intent: IntentType, session_id: str) -> str:
        """后处理响应"""
        # 清理响应格式
        cleaned_response = response.strip()
        
        # 添加适当的格式化
        if intent == IntentType.CODE_GENERATION and "```" not in cleaned_response:
            # 确保代码有适当的标记
            if "import" in cleaned_response or "def " in cleaned_response:
                cleaned_response = f"```python\n{cleaned_response}\n```"
        
        # 根据意图添加结尾提示
        ending_prompts = {
            IntentType.DATA_ANALYSIS: "\n\n需要我为您执行具体的分析步骤吗？",
            IntentType.CODE_GENERATION: "\n\n这段代码可以直接运行，需要我帮您测试吗？",
            IntentType.VISUALIZATION: "\n\n需要我帮您实现这些可视化吗？",
            IntentType.REPORT_GENERATION: "\n\n需要我帮您完善这份报告大纲吗？"
        }
        
        if intent in ending_prompts:
            cleaned_response += ending_prompts[intent]
        
        return cleaned_response
    
    def _update_context_and_memory(
        self, 
        session_id: str, 
        user_message: str, 
        response: str,
        intent: IntentType
    ):
        """更新上下文和记忆"""
        # 添加消息到上下文
        self.context_manager.add_message(session_id, "user", user_message)
        self.context_manager.add_message(session_id, "assistant", response)
        
        # 存储意图相关信息到记忆
        self.context_manager.add_memory(
            session_id,
            MemoryType.CONTEXTUAL,
            f"last_intent_{session_id}",
            intent.value,
            importance_score=0.7
        )
        
        # 提取和存储关键信息
        self._extract_key_information(session_id, user_message, response)
    
    def _extract_key_information(self, session_id: str, user_message: str, response: str):
        """提取关键信息并存储到记忆"""
        # 提取提到的文件名
        file_pattern = r'[^\s]+\.(csv|xlsx|xls|json|txt)'
        files = re.findall(file_pattern, user_message.lower())
        if files:
            self.context_manager.add_memory(
                session_id, MemoryType.FACT, "mentioned_files", files, 0.6
            )
        
        # 提取分析主题
        if len(user_message) > 30:
            topic = user_message[:50] + "..." if len(user_message) > 50 else user_message
            self.context_manager.add_memory(
                session_id, MemoryType.CONTEXTUAL, f"topic_{int(time.time())}", topic, 0.5
            )
    
    def _calculate_confidence(self, intent: IntentType, message: str) -> float:
        """计算意图识别置信度"""
        # 基于关键词匹配计算置信度
        keywords_per_intent = {
            IntentType.DATA_ANALYSIS: ['分析', '统计', '趋势', '相关性'],
            IntentType.CODE_GENERATION: ['代码', '编程', 'python', '脚本'],
            IntentType.VISUALIZATION: ['图表', '可视化', '绘图'],
            IntentType.REPORT_GENERATION: ['报告', '文档', '总结']
        }
        
        keywords = keywords_per_intent.get(intent, [])
        matches = sum(1 for keyword in keywords if keyword in message.lower())
        confidence = min(0.9, 0.3 + (matches * 0.2))
        
        return confidence
    
    def _get_fallback_response(self, error_message: str) -> Dict[str, Any]:
        """获取回退响应"""
        return {
            "content": (
                "抱歉，处理您的请求时遇到了技术问题。"
                "请稍后重试，或尝试简化您的请求。"
            ),
            "intent": "error",
            "confidence": 0.0,
            "context_used": 0,
            "timestamp": datetime.now().isoformat(),
            "error": error_message
        }


# 便捷函数
def get_assistant_engine() -> AIAssistantEngine:
    """获取助手引擎实例"""
    return AIAssistantEngine()


def chat_with_assistant(
    session_id: str,
    message: str,
    context_mode: ContextMode = ContextMode.HYBRID,
    style_preference: Optional[ResponseStyle] = None
) -> Dict[str, Any]:
    """便捷函数：与AI助手对话"""
    engine = get_assistant_engine()
    return engine.process_message(session_id, message, context_mode, style_preference)
