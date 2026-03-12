from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

import src.core.assistant.context_manager as cm
import src.core.assistant.engine as eng


def test_context_manager_core_paths(monkeypatch) -> None:
    state_store = {
        "s1": {
            "docs_analysis_history": ["旧消息1", "旧消息2"],
            "context_memories": [
                {
                    "type": "fact",
                    "key": "k1",
                    "value": "v1",
                    "created_at": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat(),
                    "access_count": 2,
                    "importance_score": 0.7,
                }
            ],
        }
    }
    updates = []
    monkeypatch.setattr(cm, "get_session_state", lambda sid: state_store.get(sid))
    monkeypatch.setattr(cm, "update_session_state", lambda sid, payload: updates.append((sid, payload)) or True)
    monkeypatch.setattr(cm, "StateManager", lambda: object())
    monkeypatch.setattr(cm, "ErrorHandler", lambda: SimpleNamespace(handle_error=lambda *a, **k: "err"))

    manager = cm.ContextManager()
    context = manager.create_conversation_context("s1", context_mode=cm.ContextMode.HYBRID, max_context_length=50)
    assert context.messages and context.memories
    msg = manager.add_message("s1", "user", "请分析这份数据", {"a": 1})
    assert msg.role == "user"

    messages = manager.get_context_messages("s1", max_tokens=10, include_system_prompt=True)
    assert messages[0]["role"] == "system"

    memory = manager.add_memory("s1", cm.MemoryType.PREFERENCE, "style", "academic", importance_score=0.8)
    assert memory.key == "style"
    assert manager.get_memory("s1", cm.MemoryType.PREFERENCE, "style") == "academic"
    assert manager.search_memories("s1", "style")
    assert manager.clear_context("s1") is True
    assert updates


def test_enhanced_ai_assistant_and_global_helpers(monkeypatch) -> None:
    state = {}
    monkeypatch.setattr(cm, "get_session_state", lambda sid: state.get(sid))
    monkeypatch.setattr(cm, "update_session_state", lambda sid, payload: state.setdefault(sid, {}).update(payload) or True)
    monkeypatch.setattr(cm, "StateManager", lambda: object())
    monkeypatch.setattr(cm, "ErrorHandler", lambda: SimpleNamespace(handle_error=lambda *a, **k: "err"))

    assistant = cm.EnhancedAIAssistant()
    result = assistant.process_message("s2", "请帮我分析 CSV 数据", max_context_tokens=100)
    assert "content" in result and result["context_length"] >= 1

    global_one = cm.get_ai_assistant()
    global_two = cm.get_ai_assistant()
    assert global_one is global_two
    payload = cm.process_user_message("s3", "我需要报告")
    assert "content" in payload


def test_assistant_engine_main_paths(monkeypatch) -> None:
    updates = []

    class DummyContextManager:
        def __init__(self):
            self.messages = []
            self.memories = []

        def get_context_messages(self, session_id, max_tokens=None, include_system_prompt=True):
            return [{"role": "system", "content": "ctx"}]

        def add_message(self, session_id, role, content):
            self.messages.append((session_id, role, content))

        def add_memory(self, session_id, memory_type, key, value, importance_score=0.5):
            self.memories.append((session_id, memory_type, key, value, importance_score))

    monkeypatch.setattr(eng, "ContextManager", DummyContextManager)
    monkeypatch.setattr(eng, "ErrorHandler", lambda: SimpleNamespace(handle_error=lambda *a, **k: "err"))
    engine = eng.AIAssistantEngine()

    engine._api_client = SimpleNamespace(chat_completion=lambda **kwargs: {"content": "分析完成"})
    result = engine.process_message("sid", "请分析 report.csv")
    assert result["intent"] == eng.IntentType.DATA_ANALYSIS.value
    assert result["confidence"] > 0

    # simulated fallback and formatting
    engine._api_client = SimpleNamespace(chat_completion=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("down")))
    assert "```python" in engine._generate_llm_response([{"content": "请给我代码"}], "sid")
    assert engine._classify_intent("请生成代码") == eng.IntentType.CODE_GENERATION
    assert engine._classify_intent("画图表") == eng.IntentType.VISUALIZATION
    assert engine._classify_intent("写报告") == eng.IntentType.REPORT_GENERATION
    assert engine._classify_intent("help me") == eng.IntentType.HELP_REQUEST
    assert engine._classify_intent("upload file") == eng.IntentType.FILE_MANAGEMENT
    assert engine._classify_intent("hello") == eng.IntentType.GENERAL_CHAT

    post = engine._post_process_response("import os", eng.IntentType.CODE_GENERATION, "sid")
    assert "```python" in post
    assert engine._get_system_prompt(eng.IntentType.DATA_ANALYSIS, eng.ResponseStyle.ANALYTICAL)["role"] == "system"
    assert engine._format_user_message("msg", eng.IntentType.DATA_ANALYSIS, engine.response_templates[eng.IntentType.DATA_ANALYSIS])["content"].startswith("# 用户请求")

    fallback = engine._get_fallback_response("x")
    assert fallback["intent"] == "error"

    helper = eng.chat_with_assistant("sid2", "如何分析")
    assert "content" in helper
