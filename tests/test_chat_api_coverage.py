from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.api.chat_api as chat_api


class _DummyStorage:
    def __init__(self, tmp_path: Path):
        self.tmp_path = tmp_path
        self.files = {}

    def create_thread(self, metadata=None):
        return SimpleNamespace(id="thread-1")

    def get_file(self, file_id):
        meta = self.files.get(file_id)
        if not meta:
            return None
        return SimpleNamespace(filename=meta["filename"])


class _AsyncStreamResponse:
    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        self._iter = iter(self._chunks)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


def _chunk(content=None, finish_reason=None):
    delta = SimpleNamespace(content=content)
    choice = SimpleNamespace(delta=delta, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice])


@pytest.mark.asyncio
async def test_chat_completions_non_stream(monkeypatch, tmp_path: Path) -> None:
    storage = _DummyStorage(tmp_path)
    source = tmp_path / "source.txt"
    source.write_text("demo", encoding="utf-8")
    storage.files["f1"] = {"filepath": str(source), "filename": "copied.txt"}

    monkeypatch.setattr(chat_api, "storage", storage)
    monkeypatch.setattr(chat_api, "get_thread_data_sessions_active", lambda tid: str(tmp_path / tid))
    monkeypatch.setattr(chat_api, "prepare_vllm_messages", lambda messages, workspace: [{"role": "user", "content": "hello"}])
    monkeypatch.setattr(chat_api, "execute_code_safe_async", lambda code, workspace: asyncio.sleep(0, result="EXEC"))
    monkeypatch.setattr(chat_api, "render_file_block", lambda artifacts, workspace, tid, sink=None: "<File />")
    monkeypatch.setattr(chat_api, "generate_report_from_messages", lambda *a, **k: "\nREPORT")
    monkeypatch.setattr(chat_api, "extract_code_from_segment", lambda s: "print(1)")

    class _Tracker:
        def __init__(self, *args, **kwargs):
            pass

        def diff_and_collect(self):
            return [tmp_path / "artifact.txt"]

    monkeypatch.setattr(chat_api, "WorkspaceTracker", _Tracker)
    async def _create_async_response(**kwargs):
        return _AsyncStreamResponse(
            [_chunk("<Code>print(1)</Code>", None), _chunk("</Answer>", "stop")]
        )
    monkeypatch.setattr(
        chat_api.vllm_client_async.chat.completions,
        "create",
        _create_async_response,
    )

    result = await chat_api.chat_completions(
        model="demo",
        messages=[{"role": "user", "content": "hello", "file_ids": ["f1"]}],
        file_ids=["f1"],
        stream=False,
    )
    assert result["choices"][0]["message"]["role"] == "assistant"
    assert "generated_files" in result or "attached_files" in result


@pytest.mark.asyncio
async def test_chat_completions_stream_and_missing_file(monkeypatch, tmp_path: Path) -> None:
    storage = _DummyStorage(tmp_path)
    monkeypatch.setattr(chat_api, "storage", storage)
    monkeypatch.setattr(chat_api, "get_thread_data_sessions_active", lambda tid: str(tmp_path / tid))
    monkeypatch.setattr(chat_api, "prepare_vllm_messages", lambda messages, workspace: [{"role": "user", "content": "hello"}])
    monkeypatch.setattr(chat_api, "execute_code_safe", lambda code, workspace: "EXEC")
    monkeypatch.setattr(chat_api, "render_file_block", lambda artifacts, workspace, tid, sink=None: "")
    monkeypatch.setattr(chat_api, "generate_report_from_messages", lambda *a, **k: "")
    monkeypatch.setattr(chat_api, "extract_code_from_segment", lambda s: None)

    class _Tracker:
        def __init__(self, *args, **kwargs):
            pass

        def diff_and_collect(self):
            return []

    monkeypatch.setattr(chat_api, "WorkspaceTracker", _Tracker)

    # missing file path raises
    with pytest.raises(chat_api.HTTPException):
        await chat_api.chat_completions(model="demo", messages=[{"role": "user", "content": "x"}], file_ids=["missing"], stream=False)

    monkeypatch.setattr(
        chat_api.vllm_client.chat.completions,
        "create",
        lambda **kwargs: iter([_chunk("hello", None), _chunk("</Answer>", "stop")]),
    )
    response = await chat_api.chat_completions(model="demo", messages=[{"role": "user", "content": "x"}], stream=True)
    assert isinstance(response, chat_api.StreamingResponse)
