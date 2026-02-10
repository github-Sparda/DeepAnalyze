"""
Enhanced AI Assistant Context Management System
增强版AI助手上下文对话管理系统
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..state.manager import StateManager, get_session_state, update_session_state
from ..error.handler import ErrorHandler, ErrorSeverity, ErrorCategory


class ContextMode(Enum):
    """上下文模式"""
    SHORT_TERM = "short_term"    # 短期上下文（当前对话轮次）
    LONG_TERM = "long_term"      # 长期上下文（跨会话记忆）
    HYBRID = "hybrid"           # 混合模式（短期+长期）


class MemoryType(Enum):
    """记忆类型"""
    CONVERSATION = "conversation"  # 对话历史
    FACT = "fact"                 # 事实信息
    PREFERENCE = "preference"     # 用户偏好
    SKILL = "skill"               # 技能知识
    CONTEXTUAL = "contextual"     # 上下文信息


@dataclass
class Message:
    """消息结构"""
    id: str
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class ContextMemory:
    """上下文记忆"""
    type: MemoryType
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    importance_score: float = 0.0  # 重要性评分 (0-1)


@dataclass
class ConversationContext:
    """对话上下文"""
    session_id: str
    messages: List[Message] = field(default_factory=list)
    memories: List[ContextMemory] = field(default_factory=list)
    context_mode: ContextMode = ContextMode.SHORT_TERM
    max_context_length: int = 10000  # 最大上下文长度（token数）
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class ContextManager:
    """上下文管理器"""
    
    def __init__(self, state_manager: Optional[StateManager] = None):
        self.state_manager = state_manager or StateManager()
        self.error_handler = ErrorHandler()
        self.conversation_data_cache: Dict[str, ConversationContext] = {}
    
    def create_conversation_context(
        self, 
        session_id: str,
        context_mode: ContextMode = ContextMode.SHORT_TERM,
        max_context_length: int = 10000
    ) -> ConversationContext:
        """创建对话上下文"""
        context = ConversationContext(
            session_id=session_id,
            context_mode=context_mode,
            max_context_length=max_context_length
        )
        
        # 从状态管理器加载历史上下文
        state = get_session_state(session_id)
        if state:
            # 恢复历史消息
            history = state.get('docs_analysis_history', [])
            for i, history_item in enumerate(history[-10:]):  # 最近10条
                message = Message(
                    id=f"hist_{i}_{int(time.time())}",
                    role="assistant",
                    content=history_item,
                    timestamp=datetime.now()
                )
                context.messages.append(message)
            
            # 恢复记忆信息
            self._restore_memories(context, state)
        
        self.conversation_data_cache[session_id] = context
        return context
    
    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """添加消息到上下文"""
        try:
            context = self.get_context(session_id)
            if not context:
                context = self.create_conversation_context(session_id)
            
            message = Message(
                id=f"msg_{len(context.messages)}_{int(time.time())}",
                role=role,
                content=content,
                timestamp=datetime.now(),
                metadata=metadata or {}
            )
            
            context.messages.append(message)
            context.updated_at = datetime.now()
            
            # 更新到状态管理器
            self._update_state_with_context(session_id, context)
            
            # 如果超出最大长度，进行压缩
            self._compress_context_if_needed(context)
            
            return message
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.EXECUTION,
                context={"session_id": session_id, "role": role}
            )
            raise e
    
    def get_context_messages(
        self, 
        session_id: str, 
        max_tokens: Optional[int] = None,
        include_system_prompt: bool = True
    ) -> List[Dict[str, Any]]:
        """获取格式化的上下文消息"""
        context = self.get_context(session_id)
        if not context:
            return []
        
        messages = []
        
        # 添加系统提示
        if include_system_prompt:
            system_message = self._get_system_prompt(context)
            if system_message:
                messages.append(system_message)
        
        # 添加历史消息
        relevant_messages = self._get_relevant_messages(context, max_tokens)
        
        for msg in relevant_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            })
        
        return messages
    
    def add_memory(
        self,
        session_id: str,
        memory_type: MemoryType,
        key: str,
        value: Any,
        importance_score: float = 0.5
    ) -> ContextMemory:
        """添加记忆"""
        try:
            context = self.get_context(session_id)
            if not context:
                context = self.create_conversation_context(session_id)
            
            memory = ContextMemory(
                type=memory_type,
                key=key,
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=1,
                importance_score=importance_score
            )
            
            # 检查是否已存在相同key的记忆
            existing_index = None
            for i, existing_memory in enumerate(context.memories):
                if existing_memory.key == key and existing_memory.type == memory_type:
                    existing_index = i
                    break
            
            if existing_index is not None:
                # 更新现有记忆
                context.memories[existing_index] = memory
            else:
                # 添加新记忆
                context.memories.append(memory)
            
            # 更新状态
            self._update_state_with_context(session_id, context)
            
            # 清理低重要性记忆
            self._prune_low_importance_memories(context)
            
            return memory
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.EXECUTION,
                context={"session_id": session_id, "memory_type": memory_type.value}
            )
            raise e
    
    def get_memory(
        self, 
        session_id: str, 
        memory_type: MemoryType, 
        key: str
    ) -> Optional[Any]:
        """获取记忆"""
        context = self.get_context(session_id)
        if not context:
            return None
        
        for memory in context.memories:
            if memory.type == memory_type and memory.key == key:
                memory.access_count += 1
                memory.last_accessed = datetime.now()
                return memory.value
        
        return None
    
    def search_memories(
        self,
        session_id: str,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        top_k: int = 5
    ) -> List[ContextMemory]:
        """搜索相关记忆"""
        context = self.get_context(session_id)
        if not context:
            return []
        
        # 简单的关键词匹配（后续可替换为向量搜索）
        relevant_memories = []
        query_lower = query.lower()
        
        for memory in context.memories:
            if memory_types and memory.type not in memory_types:
                continue
                
            # 检查key和value中是否包含查询词
            memory_text = f"{memory.key} {str(memory.value)}".lower()
            if query_lower in memory_text:
                # 计算相关性分数
                relevance_score = memory.importance_score
                if query_lower == memory.key.lower():
                    relevance_score += 0.3  # 完全匹配key加分
                
                memory.relevance_score = relevance_score
                relevant_memories.append(memory)
        
        # 按相关性排序
        relevant_memories.sort(
            key=lambda x: getattr(x, 'relevance_score', x.importance_score), 
            reverse=True
        )
        
        return relevant_memories[:top_k]
    
    def get_context(self, session_id: str) -> Optional[ConversationContext]:
        """获取对话上下文"""
        # 先从缓存获取
        if session_id in self.conversation_data_cache:
            return self.conversation_data_cache[session_id]
        
        # 从状态管理器重建
        state = get_session_state(session_id)
        if state:
            context = self.create_conversation_context(session_id)
            return context
        
        return None
    
    def clear_context(self, session_id: str) -> bool:
        """清除对话上下文"""
        try:
            # 清除缓存
            if session_id in self.conversation_data_cache:
                del self.conversation_data_cache[session_id]
            
            # 清除状态中的上下文信息
            state_updates = {
                'docs_analysis_history': [],
                'context_memories': []
            }
            success = update_session_state(session_id, state_updates)
            
            return success
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.EXECUTION,
                context={"session_id": session_id}
            )
            return False
    
    def _get_system_prompt(self, context: ConversationContext) -> Optional[Dict[str, Any]]:
        """获取系统提示"""
        system_prompts = {
            ContextMode.SHORT_TERM: (
                "你是一个专业的数据分析AI助手。请基于用户提供的数据和问题，"
                "给出准确、详细的分析建议和解决方案。"
            ),
            ContextMode.LONG_TERM: (
                "你是一个具备长期记忆能力的数据分析专家。除了当前对话，"
                "你还记得之前的交流内容和用户偏好，请提供更加个性化的服务。"
            ),
            ContextMode.HYBRID: (
                "你是一个智能数据分析助手，能够结合当前对话和历史记忆，"
                "提供既准确又个性化的分析服务。"
            )
        }
        
        prompt = system_prompts.get(context.context_mode)
        if prompt:
            return {"role": "system", "content": prompt}
        return None
    
    def _get_relevant_messages(
        self, 
        context: ConversationContext, 
        max_tokens: Optional[int] = None
    ) -> List[Message]:
        """获取相关的消息（考虑token限制）"""
        if not max_tokens:
            return context.messages[-20:]  # 默认返回最近20条
        
        # 简单的token估算（每个字符约0.25个token）
        total_tokens = 0
        relevant_messages = []
        
        # 从最新消息开始向前遍历
        for message in reversed(context.messages):
            message_tokens = len(message.content) * 0.25
            if total_tokens + message_tokens > max_tokens and relevant_messages:
                break
            relevant_messages.append(message)
            total_tokens += message_tokens
        
        return list(reversed(relevant_messages))
    
    def _compress_context_if_needed(self, context: ConversationContext):
        """如果需要，压缩上下文"""
        # 估算总token数
        total_chars = sum(len(msg.content) for msg in context.messages)
        estimated_tokens = total_chars * 0.25
        
        if estimated_tokens > context.max_context_length:
            # 保留最近的重要消息
            important_messages = []
            recent_messages = context.messages[-10:]  # 最近10条
            
            # 保留包含关键信息的消息
            for msg in recent_messages:
                content_lower = msg.content.lower()
                if any(keyword in content_lower for keyword in [
                    '分析', '数据', '结果', '结论', '建议', '代码', 'error'
                ]):
                    important_messages.append(msg)
            
            # 如果重要消息太少，补充一些其他消息
            if len(important_messages) < 5:
                additional_needed = 5 - len(important_messages)
                other_messages = [msg for msg in recent_messages if msg not in important_messages]
                important_messages.extend(other_messages[:additional_needed])
            
            context.messages = important_messages
    
    def _prune_low_importance_memories(self, context: ConversationContext):
        """清理低重要性的记忆"""
        # 保留重要性评分高于0.3的记忆
        context.memories = [
            memory for memory in context.memories 
            if memory.importance_score > 0.3
        ]
        
        # 如果记忆太多，保留最重要的
        if len(context.memories) > 50:
            context.memories.sort(key=lambda x: x.importance_score, reverse=True)
            context.memories = context.memories[:50]
    
    def _restore_memories(self, context: ConversationContext, state: Dict[str, Any]):
        """从状态中恢复记忆"""
        memory_data = state.get('context_memories', [])
        for mem_dict in memory_data:
            try:
                memory = ContextMemory(
                    type=MemoryType(mem_dict['type']),
                    key=mem_dict['key'],
                    value=mem_dict['value'],
                    created_at=datetime.fromisoformat(mem_dict['created_at']),
                    last_accessed=datetime.fromisoformat(mem_dict['last_accessed']),
                    access_count=mem_dict.get('access_count', 0),
                    importance_score=mem_dict.get('importance_score', 0.5)
                )
                context.memories.append(memory)
            except Exception:
                continue  # 跳过无效的记忆数据
    
    def _update_state_with_context(self, session_id: str, context: ConversationContext):
        """将上下文更新到状态管理器"""
        # 转换记忆为可序列化格式
        memory_dicts = []
        for memory in context.memories:
            memory_dicts.append({
                'type': memory.type.value,
                'key': memory.key,
                'value': memory.value,
                'created_at': memory.created_at.isoformat(),
                'last_accessed': memory.last_accessed.isoformat(),
                'access_count': memory.access_count,
                'importance_score': memory.importance_score
            })
        
        # 更新状态
        state_updates = {
            'docs_analysis_history': [msg.content for msg in context.messages[-10:]],
            'context_memories': memory_dicts,
            'last_context_update': datetime.now().isoformat()
        }
        
        update_session_state(session_id, state_updates)


class EnhancedAIAssistant:
    """增强版AI助手"""
    
    def __init__(self):
        self.context_manager = ContextManager()
        self.error_handler = ErrorHandler()
    
    def process_message(
        self,
        session_id: str,
        user_message: str,
        context_mode: ContextMode = ContextMode.HYBRID,
        max_context_tokens: int = 8000
    ) -> Dict[str, Any]:
        """处理用户消息"""
        try:
            # 添加用户消息到上下文
            self.context_manager.add_message(
                session_id, 
                "user", 
                user_message,
                {"source": "direct_input"}
            )
            
            # 获取上下文消息
            context_messages = self.context_manager.get_context_messages(
                session_id,
                max_tokens=max_context_tokens
            )
            
            # 添加当前用户消息
            context_messages.append({
                "role": "user",
                "content": user_message
            })
            
            # 这里应该调用实际的LLM API
            # 暂时返回模拟响应
            response_content = self._generate_response(context_messages, session_id)
            
            # 添加助手响应到上下文
            assistant_message = self.context_manager.add_message(
                session_id,
                "assistant",
                response_content,
                {"response_type": "analysis"}
            )
            
            # 提取和存储重要信息到记忆
            self._extract_and_store_memories(session_id, user_message, response_content)
            
            return {
                "message_id": assistant_message.id,
                "content": response_content,
                "context_length": len(context_messages),
                "timestamp": assistant_message.timestamp.isoformat()
            }
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.EXECUTION,
                context={"session_id": session_id}
            )
            return {
                "error": str(e),
                "message_id": f"error_{int(time.time())}",
                "content": "抱歉，处理您的请求时出现了错误。请稍后重试。",
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_response(self, messages: List[Dict[str, Any]], session_id: str) -> str:
        """生成AI响应（模拟实现）"""
        # 实际实现中这里会调用LLM API
        last_user_message = messages[-1]['content'] if messages else ""
        
        # 基于消息内容生成适当的响应
        if "分析" in last_user_message or "数据" in last_user_message:
            return "我理解您想要进行数据分析。请上传您的数据文件，我将帮您进行全面的分析，包括数据清洗、统计分析、可视化和洞察发现。"
        elif "报告" in last_user_message:
            return "我很乐意帮您生成分析报告。请告诉我您希望报告包含哪些方面的内容，以及您偏好的报告格式（学术风格、商业报告等）。"
        elif "帮助" in last_user_message or "如何" in last_user_message:
            return "我是您的数据分析AI助手。您可以：\n1. 上传CSV/Excel文件进行分析\n2. 询问具体的数据问题\n3. 请求生成可视化图表\n4. 要求制作分析报告\n请问有什么我可以帮助您的吗？"
        else:
            return "感谢您的消息。我是数据分析AI助手，专门帮助您处理数据、生成洞察和创建报告。请告诉我您想要分析什么数据或解决什么问题？"
    
    def _extract_and_store_memories(self, session_id: str, user_message: str, response: str):
        """从对话中提取并存储重要记忆"""
        # 提取用户偏好
        if "学术" in user_message or "研究" in user_message:
            self.context_manager.add_memory(
                session_id, MemoryType.PREFERENCE, "report_style", "academic", 0.8
            )
        elif "商业" in user_message or "业务" in user_message:
            self.context_manager.add_memory(
                session_id, MemoryType.PREFERENCE, "report_style", "business", 0.8
            )
        
        # 提取数据相关事实
        if "CSV" in user_message or "Excel" in user_message:
            self.context_manager.add_memory(
                session_id, MemoryType.FACT, "data_format_mentioned", True, 0.6
            )
        
        # 存储对话主题
        if len(user_message) > 20:  # 较长的消息可能包含重要信息
            self.context_manager.add_memory(
                session_id, 
                MemoryType.CONTEXTUAL, 
                f"topic_{int(time.time())}", 
                user_message[:100],  # 存储前100个字符
                0.4
            )


# 全局实例
_ai_assistant: Optional[EnhancedAIAssistant] = None


def get_ai_assistant() -> EnhancedAIAssistant:
    """获取全局AI助手实例"""
    global _ai_assistant
    if _ai_assistant is None:
        _ai_assistant = EnhancedAIAssistant()
    return _ai_assistant


def process_user_message(
    session_id: str,
    message: str,
    context_mode: ContextMode = ContextMode.HYBRID,
    max_context_tokens: int = 8000
) -> Dict[str, Any]:
    """便捷函数：处理用户消息"""
    assistant = get_ai_assistant()
    return assistant.process_message(session_id, message, context_mode, max_context_tokens)
