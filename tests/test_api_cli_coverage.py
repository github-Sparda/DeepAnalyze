from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


class _DummyConsole:
    def print(self, *args, **kwargs):
        return None


class _DummyFiles:
    def __init__(self):
        self.created = []
        self.deleted = []

    def create(self, file, purpose):
        name = Path(getattr(file, "name", "uploaded.txt")).name
        obj = SimpleNamespace(id=f"file-{len(self.created)+1}", filename=name, purpose=purpose)
        self.created.append(obj)
        return obj

    def delete(self, file_id):
        self.deleted.append(file_id)

    def content(self, file_id):
        return SimpleNamespace(content=b"downloaded")


class _DummyClient:
    def __init__(self):
        self.files = _DummyFiles()
        self.models = SimpleNamespace(list=lambda: ["m1"])


@pytest.fixture(params=["src.cli.api_cli", "src.cli.api_cli_ZH"])
def cli_module(request):
    import src.api.config as api_config

    sys.modules.setdefault("config", api_config)
    return importlib.import_module(request.param)


def _build_cli(monkeypatch, cli_module):
    monkeypatch.setattr(cli_module.DeepAnalyzeCLI, "setup_command_history", lambda self: setattr(self, "history_file", "/tmp/history"))
    monkeypatch.setattr(cli_module, "console", _DummyConsole())
    return cli_module.DeepAnalyzeCLI()


def test_api_cli_core_file_management(monkeypatch, tmp_path: Path, cli_module) -> None:
    cli = _build_cli(monkeypatch, cli_module)
    dummy_client = _DummyClient()

    monkeypatch.setattr(cli_module.openai, "OpenAI", lambda api_key, base_url: dummy_client)
    assert cli.initialize_client() is True
    assert cli.client is dummy_client

    data_file = tmp_path / "sample.txt"
    data_file.write_text("payload", encoding="utf-8")
    file_id = cli.upload_file(str(data_file))
    assert file_id == "file-1"
    assert cli.uploaded_files[0]["name"] == "sample.txt"

    cli.list_uploaded_files()
    assert cli.is_intermediate_file({"name": "result.json"}) is True
    assert cli.is_intermediate_file({"name": "report.md"}) is False

    class _Resp:
        status_code = 200
        content = b"mid"

    import requests

    monkeypatch.setattr(requests, "get", lambda url: _Resp())
    intermediate_id = cli.upload_intermediate_file({"name": "artifact.json", "url": "http://x/artifact.json"})
    assert intermediate_id == "file-2"
    assert cli.intermediate_files[0]["name"] == "artifact.json"

    assert cli.delete_file_by_id("file-1") is True
    cli.uploaded_files.append({"id": "file-3", "name": "download.txt", "size": 10})
    save_path = tmp_path / "download.bin"
    cli.download_file_by_id("file-3", str(save_path))
    assert save_path.exists() and save_path.read_bytes() == b"downloaded"


def test_api_cli_command_and_history_paths(monkeypatch, cli_module) -> None:
    cli = _build_cli(monkeypatch, cli_module)
    cli.client = _DummyClient()
    cli.uploaded_files = [{"id": "f1", "name": "u.txt", "size": 1, "purpose": "assistants"}]
    cli.intermediate_files = [{"id": "f2", "name": "mid.json", "purpose": "assistants"}]
    cli.generated_files = [{"name": "report.md", "url": "http://r", "type": "output", "size": 10}]
    cli.chat_history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "world"},
    ]

    called = []
    monkeypatch.setattr(cli_module.Confirm, "ask", staticmethod(lambda *args, **kwargs: True))
    monkeypatch.setattr(cli, "show_help", lambda: called.append("help"))
    monkeypatch.setattr(cli, "clear_chat_history", lambda: called.append("clear"))
    monkeypatch.setattr(cli, "clear_all", lambda: called.append("clear-all"))
    monkeypatch.setattr(cli, "list_uploaded_files", lambda: called.append("files"))
    monkeypatch.setattr(cli, "upload_file", lambda path: called.append(f"upload:{path}"))
    monkeypatch.setattr(cli, "delete_file_by_id", lambda fid: called.append(f"delete:{fid}"))
    monkeypatch.setattr(cli, "download_file_by_id", lambda fid, path=None: called.append(f"download:{fid}:{path}"))
    monkeypatch.setattr(cli, "get_system_status", lambda: called.append("status"))
    monkeypatch.setattr(cli, "show_history", lambda: called.append("history"))
    monkeypatch.setattr(cli, "show_file_ids", lambda: called.append("fid"))

    assert cli.handle_command("help") is True
    assert cli.handle_command("clear") is True
    assert cli.handle_command("clear-all") is True
    assert cli.handle_command("files") is True
    assert cli.handle_command("upload abc.txt") is True
    assert cli.handle_command("delete f1") is True
    assert cli.handle_command("download f1 /tmp/x") is True
    assert cli.handle_command("status") is True
    assert cli.handle_command("history") is True
    assert cli.handle_command("fid") is True
    assert cli.handle_command("not-a-command") is False
    assert called


def test_api_cli_runtime_paths(monkeypatch, tmp_path: Path, cli_module) -> None:
    cli = _build_cli(monkeypatch, cli_module)
    dummy_client = _DummyClient()
    cli.client = dummy_client

    import requests

    monkeypatch.setattr(requests, "get", lambda url, timeout=5: SimpleNamespace(status_code=200))
    assert cli.check_server() is True

    cli.show_history()
    cli.show_file_ids()
    cli.get_system_status()

    cli.uploaded_files = [{"id": "f1", "name": "u.txt", "size": 1, "purpose": "assistants"}]
    cli.intermediate_files = [{"id": "f2", "name": "m.txt", "purpose": "assistants"}]
    cli.generated_files = [{"name": "report.md", "type": "output"}]
    cli.clear_chat_history()
    assert cli.chat_history == []
    cli.clear_all()
    assert cli.uploaded_files == []

    cli.uploaded_files = [{"id": "f3", "name": "left.txt", "size": 1, "purpose": "assistants"}]
    cli.cleanup_files()
    assert cli.uploaded_files == []

    monkeypatch.setattr(cli, "check_server", lambda: True)
    monkeypatch.setattr(cli, "display_header", lambda: None)
    monkeypatch.setattr(cli, "interactive_mode", lambda: setattr(cli, "_entered", True))
    cli.run()
    assert cli._entered is True

    monkeypatch.setattr(cli, "check_server", lambda: False)
    cli.run()


def test_api_cli_chat_and_error_paths(monkeypatch, tmp_path: Path, cli_module) -> None:
    cli = _build_cli(monkeypatch, cli_module)
    dummy_client = _DummyClient()
    cli.client = dummy_client
    cli.uploaded_files = [{"id": "u1", "name": "source.csv", "size": 1, "purpose": "assistants"}]

    class _Delta:
        def __init__(self, content):
            self.content = content

    class _Chunk:
        def __init__(self, content=None, generated_files=None):
            self.choices = [SimpleNamespace(delta=_Delta(content))]
            self.generated_files = generated_files

    generated = [
        {"name": "artifact.json", "url": "http://example.com/artifact.json", "id": "g1"},
        {"name": "report.md", "url": "http://example.com/report.md", "id": "g2"},
    ]
    dummy_client.chat = SimpleNamespace(
        completions=SimpleNamespace(
            create=lambda **kwargs: iter([_Chunk("hello "), _Chunk("world", generated_files=generated)])
        )
    )

    import requests
    monkeypatch.setattr(requests, "get", lambda url, timeout=None: SimpleNamespace(status_code=200, content=b"abc"))
    monkeypatch.setattr(requests, "head", lambda url, timeout=None: SimpleNamespace(status_code=200, headers={"content-length": "3"}))
    original_upload_intermediate_file = cli.upload_intermediate_file
    monkeypatch.setattr(cli, "upload_intermediate_file", lambda file_info: "mid-1")
    text = cli.chat_with_file("analyze")
    assert text == "hello world"
    assert cli.chat_history[-1]["role"] == "assistant"
    assert any(f["type"] == "output" for f in cli.generated_files)

    # no client and initialize failure
    cli.client = None
    monkeypatch.setattr(cli, "initialize_client", lambda: False)
    assert cli.chat_with_file("again") is None

    # upload intermediate failure branches
    cli.client = dummy_client
    monkeypatch.setattr(cli, "upload_intermediate_file", original_upload_intermediate_file)
    monkeypatch.setattr(requests, "get", lambda url: SimpleNamespace(status_code=500, content=b""))
    assert cli.upload_intermediate_file({"name": "x.json", "url": "http://bad"}) is None
    monkeypatch.setattr(requests, "get", lambda url: (_ for _ in ()).throw(RuntimeError("net")))
    assert cli.upload_intermediate_file({"name": "x.json", "url": "http://bad"}) is None

    # delete/download failure
    cli.client = None
    monkeypatch.setattr(cli, "initialize_client", lambda: False)
    assert cli.delete_file_by_id("missing") is False
    cli.download_file_by_id("missing", str(tmp_path / "out.bin"))


def test_api_cli_history_interactive_and_main(monkeypatch, cli_module) -> None:
    cli = _build_cli(monkeypatch, cli_module)
    cli.chat_history = [{"role": "user", "content": "u" * 120}, {"role": "assistant", "content": "a"}]
    cli.generated_files = [{"type": "output"}, {"type": "intermediate"}]
    cli.show_history()

    inputs = iter(["", "hello", "quit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(cli, "save_history", lambda: setattr(cli, "_saved", True))
    monkeypatch.setattr(cli, "handle_command", lambda user_input: False)
    monkeypatch.setattr(cli, "chat_with_file", lambda message, file_ids=None, stream=True: setattr(cli, "_chat", (message, file_ids, stream)))
    cli.interactive_mode()
    assert cli._saved is True
    assert cli._chat[0] == "hello"

    monkeypatch.setattr(cli_module, "atexit", SimpleNamespace(register=lambda fn: None))
    called = []
    monkeypatch.setattr(cli_module, "DeepAnalyzeCLI", lambda: SimpleNamespace(run=lambda: called.append("run")))
    cli_module.main()
    assert called == ["run"]
