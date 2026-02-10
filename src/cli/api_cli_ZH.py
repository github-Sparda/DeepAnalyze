#!/usr/bin/env python3
"""
DeepAnalyze API CLI - 轻量级美观的命令行界面 (中文版)
使用 rich 包实现的 API 客户端，支持文件上传和数据分析任务
"""

import os
import sys
import json
import time
import readline
import atexit
from pathlib import Path
from typing import Optional, List, Dict, Any
import openai
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn
from rich.table import Table
from rich.tree import Tree
from rich.markdown import Markdown
from rich.rule import Rule
from rich.columns import Columns
from rich.text import Text
from rich.live import Live
from rich.syntax import Syntax
from rich.filesize import decimal

from pathlib import Path

API_DIR = Path(__file__).resolve().parents[2] / "src/api"
if str(API_DIR) not in sys.path:
    sys.path.append(str(API_DIR))

from config import (
    API_PUBLIC_BASE,
    API_PUBLIC_BASE_V1,
    DEFAULT_MODEL,
    DEEPANALYZE_VLLM_API_KEY,
    MAX_RECURSION_DEPTH,
    REPORT_EXPORT_MODE,
    REPORT_FORMAT,
    REPORT_LANGUAGE,
    VISUAL_INTERACTIVE,
    VISUAL_STYLE,
)

console = Console()

class DeepAnalyzeCLI:
    def __init__(self):
        """初始化CLI客户端"""
        self.api_base = API_PUBLIC_BASE_V1
        self.model = DEFAULT_MODEL
        self.client = None
        self.uploaded_files = []
        self.current_thread_id = None
        self.chat_history = []  # 聊天历史
        self.generated_files = []  # 生成的文件（包括报告、图片等）
        self.intermediate_files = []  # 中间文件（上传的生成文件用于对话）
        self.setup_command_history()

    def setup_command_history(self):
        """设置命令历史功能"""
        history_file = os.path.expanduser("~/.deeppanalyze_history_zh")

        # 尝试读取历史文件
        try:
            if os.path.exists(history_file):
                readline.read_history_file(history_file)
            # 设置历史文件长度限制
            readline.set_history_length(1000)
            # 每次命令后自动保存历史
            readline.set_auto_history(True)
        except Exception as e:
            # 静默处理失败
            pass

        self.history_file = history_file

    def save_history(self):
        """保存历史到文件"""
        try:
            if hasattr(self, 'history_file'):
                readline.write_history_file(self.history_file)
        except Exception as e:
            # 静默处理失败
            pass

    def initialize_client(self):
        """初始化OpenAI客户端"""
        try:
            self.client = openai.OpenAI(
                api_key=DEEPANALYZE_VLLM_API_KEY,
                base_url=self.api_base
            )
            return True
        except Exception as e:
            console.print(f"[red]❌ 客户端初始化失败: {e}[/red]")
            return False

    def check_server(self) -> bool:
        """检查API服务器是否运行"""
        try:
            import requests
            # 首先尝试检查健康端点
            response = requests.get(f"{API_PUBLIC_BASE}/health", timeout=5)
            if response.status_code == 200:
                return True

            # 如果健康端点不可用，尝试检查模型列表
            temporary_client = openai.OpenAI(api_key=DEEPANALYZE_VLLM_API_KEY, base_url=self.api_base)
            models = temporary_client.models.list()
            return True
        except:
            return False

    def display_header(self):
        """显示程序头部信息"""
        header_content = f"""[bold cyan]🚀 DeepAnalyze API 客户端[/bold cyan]
[dim]API服务器: {API_PUBLIC_BASE} | 模型: {DEFAULT_MODEL}[/dim]"""

        console.print(Panel(header_content, title="DeepAnalyze CLI", border_style="cyan"))

    def upload_file(self, file_path: str) -> Optional[str]:
        """上传文件到API服务器"""
        try:
            full_path = Path(file_path).expanduser().resolve()
            if not full_path.exists():
                console.print(f"[red]❌ 文件不存在: {file_path}[/red]")
                return None

            if not self.client:
                if not self.initialize_client():
                    return None

            file_size = full_path.stat().st_size

            # 安全处理文件名以避免编码错误
            safe_filename = full_path.name
            try:
                # 确保文件名可以安全编码
                safe_filename.encode('utf-8')
            except UnicodeEncodeError:
                # 如果文件名包含无效字符，使用安全文件名
                safe_filename = f"file_{int(time.time())}{full_path.suffix}"

            # 显示上传开始消息
            console.print(f"[cyan]📤 正在上传 {safe_filename}...[/cyan]")

            # 使用OpenAI库上传文件
            with open(full_path, 'rb') as f:
                file_obj = self.client.files.create(
                    file=f,
                    purpose="assistants"
                )

            # 安全处理返回的文件名
            safe_response_filename = file_obj.filename
            try:
                safe_response_filename.encode('utf-8')
            except UnicodeEncodeError:
                safe_response_filename = safe_filename  # 使用我们的安全文件名

            self.uploaded_files.append({
                'id': file_obj.id,
                'name': safe_response_filename,
                'path': str(full_path),
                'size': file_size,
                'purpose': file_obj.purpose
            })

            console.print("[green]✅ 文件上传成功![/green]")
            console.print(f"[dim]文件ID: {file_obj.id}[/dim]")
            console.print(f"[dim]文件名: {safe_response_filename}[/dim]")
            console.print(f"[dim]文件大小: {decimal(file_size)}[/dim]")
            console.print(f"[dim]用途: {file_obj.purpose}[/dim]")
            return file_obj.id

        except Exception as e:
            console.print(f"[red]❌ 上传错误: {e}[/red]")
            return None

    def list_uploaded_files(self):
        """显示所有文件列表（用户上传文件、中间文件和输出文件）"""
        # 获取输出文件（图片和MD报告）
        output_files = [f for f in self.generated_files if f.get('type') == 'output']

        # 检查是否有任何文件
        if not self.uploaded_files and not self.intermediate_files and not output_files:
            console.print("[yellow]📝 暂无文件[/yellow]")
            return

        # 显示用户上传文件
        if self.uploaded_files:
            table = Table(title="用户上传文件", show_header=True, header_style="bold magenta")
            table.add_column("文件名", style="cyan", no_wrap=True)
            table.add_column("文件ID", style="green")
            table.add_column("文件大小", style="yellow")
            table.add_column("用途", style="blue")
            table.add_column("状态", style="green")

            for file_info in self.uploaded_files:
                table.add_row(
                    file_info['name'],
                    file_info['id'][:8] + "...",
                    decimal(file_info['size']),
                    file_info.get('purpose', 'assistants'),
                    "✅ 已上传"
                )

            console.print(table)

        # 显示中间文件
        if self.intermediate_files:
            if self.uploaded_files:
                console.print()  # 添加空行分隔符

            intermediate_table = Table(title="生成中间文件", show_header=True, header_style="bold cyan")
            intermediate_table.add_column("文件名", style="cyan", no_wrap=True)
            intermediate_table.add_column("文件ID", style="green")
            intermediate_table.add_column("URL", style="blue")
            intermediate_table.add_column("来源", style="yellow")
            intermediate_table.add_column("用途", style="blue")
            intermediate_table.add_column("状态", style="orange3")

            for file_info in self.intermediate_files:
                file_name = file_info['name']
                original_url = file_info.get('original_url', '')

                # 为中间文件创建超链接URL显示
                if original_url:
                    display_url = original_url[:60] + "..." if len(original_url) > 60 else original_url
                    url_text = Text(display_url, style="blue")
                    url_text.stylize(f"link {original_url}")
                else:
                    url_text = Text("无URL", style="blue")

                intermediate_table.add_row(
                    file_name,
                    file_info['id'][:8] + "...",
                    url_text,
                    "AI生成",
                    file_info.get('purpose', 'assistants'),
                    "🔄 中间文件"
                )

            console.print(intermediate_table)

        # 显示输出文件（图片和MD报告）
        if output_files:
            if self.uploaded_files or self.intermediate_files:
                console.print()  # 添加空行分隔符

            output_table = Table(title="生成输出文件", show_header=True, header_style="bold green")
            output_table.add_column("文件名", style="cyan", no_wrap=True)
            output_table.add_column("URL", style="blue")
            output_table.add_column("来源", style="yellow")
            output_table.add_column("大小", style="magenta")
            output_table.add_column("状态", style="bright_blue")

            for file_info in output_files:
                file_name = file_info.get('name', '未知文件')
                file_url = file_info.get('url', '无URL')
                file_size = file_info.get('size', '未知')

                # 根据扩展名确定文件类型
                if file_name.lower().endswith(('.md', '.markdown')):
                    file_type = "报告"
                elif file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp')):
                    file_type = "图片"
                else:
                    file_type = "输出"
                # 创建超链接URL显示（显示截断文本，但链接到完整URL）
                if file_url != '无URL':
                    display_url = file_url[:60] + "..." if len(file_url) > 60 else file_url
                    url_text = Text(display_url, style="blue")
                    url_text.stylize(f"link {file_url}")
                else:
                    url_text = Text("无URL", style="blue")

                # 确定文件大小显示
                size_display = str(file_size) if file_size != '未知' else "未知"

                output_table.add_row(
                    file_name,
                    url_text,
                    file_type,
                    size_display,
                    "📋 已生成"
                )

            console.print(output_table)

        # 显示说明信息
        if self.intermediate_files or output_files:
            console.print()
            explanations = []
            if self.intermediate_files:
                explanations.append("🔄 中间文件: AI生成的数据文件，自动上传用于后续对话上下文")
            if output_files:
                explanations.append("📋 输出文件: AI生成的报告和图片，可通过URL直接访问")

            for explanation in explanations:
                console.print(f"[dim]{explanation}[/dim]")

    def is_intermediate_file(self, file_info: Dict[str, Any]) -> bool:
        """判断文件是否应该作为中间文件上传（排除报告和图片）"""
        file_name = file_info.get('name', '').lower()

        # 排除报告文件和图片文件
        intermediate_extensions = ['.md', '.markdown', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp']

        # 检查文件扩展名
        for ext in intermediate_extensions:
            if file_name.endswith(ext):
                return False

        # 其他文件作为中间文件处理
        return True

    def upload_intermediate_file(self, file_info: Dict[str, Any]) -> Optional[str]:
        """上传中间文件并返回file_id"""
        try:
            if not self.client:
                if not self.initialize_client():
                    return None

            file_name = file_info.get('name', 'unknown_file')
            file_url = file_info.get('url', '')

            # 安全处理文件名
            safe_file_name = file_name
            try:
                safe_file_name.encode('utf-8')
            except UnicodeEncodeError:
                # 如果文件名包含无效字符，使用安全文件名
                import time
                file_ext = os.path.splitext(file_name)[1]
                safe_file_name = f"intermediate_file_{int(time.time())}{file_ext}"

            console.print(f"[dim]📤 正在上传中间文件: {safe_file_name}[/dim]")

            # 尝试从URL下载文件内容并上传
            import requests
            import tempfile
            import os

            # 下载文件
            response = requests.get(file_url)
            if response.status_code == 200:
                # 创建临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(safe_file_name)[1]) as temporary_file:
                    temporary_file.write(response.content)
                    temporary_file_path = temporary_file.name

                try:
                    # 上传到API
                    with open(temporary_file_path, 'rb') as f:
                        file_obj = self.client.files.create(
                            file=f,
                            purpose="assistants"
                        )

                    # 保存到中间文件列表
                    self.intermediate_files.append({
                        'id': file_obj.id,
                        'name': safe_file_name,
                        'original_url': file_url,
                        'purpose': file_obj.purpose
                    })

                    console.print(f"[dim]✅ 中间文件上传成功: {safe_file_name} -> {file_obj.id}[/dim]")
                    return file_obj.id

                finally:
                    # 删除临时文件
                    os.unlink(temporary_file_path)
            else:
                console.print(f"[red]❌ 下载中间文件失败: {safe_file_name}[/red]")
                return None

        except Exception as e:
            console.print(f"[red]❌ 上传中间文件失败 {safe_file_name}: {e}[/red]")
            return None

    def chat_with_file(self, message: str, file_ids: List[str] = None, stream: bool = True):
        """与AI聊天进行分析"""
        try:
            if not self.client:
                if not self.initialize_client():
                    return

            # 添加用户消息到历史
            self.chat_history.append({"role": "user", "content": message})
            if file_ids:
                self.chat_history[-1]["file_ids"] = file_ids

            # 构建消息列表，包括历史对话
            messages = []

            # 添加历史对话（排除file_ids）
            for msg in self.chat_history[:-1]:  # 排除新添加的用户消息
                if msg["role"] == "user":
                    messages.append({"role": "user", "content": msg["content"]})
                elif msg["role"] == "assistant":
                    messages.append({"role": "assistant", "content": msg["content"]})

            # 获取所有文件ID：上传文件 + 中间文件
            all_file_ids = []

            # 添加上传文件ID
            uploaded_file_ids = [f['id'] for f in self.uploaded_files]
            all_file_ids.extend(uploaded_file_ids)

            # 添加中间文件ID（上传的生成文件）
            intermediate_file_ids = [f['id'] for f in self.intermediate_files]
            all_file_ids.extend(intermediate_file_ids)

            # 去重
            all_file_ids = list(set(all_file_ids))

            # 添加当前用户消息（只有此消息包含file_ids）
            current_message = {"role": "user", "content": message}
            if all_file_ids:
                current_message["file_ids"] = all_file_ids
            messages.append(current_message)

            console.print("[cyan]💭 正在分析...[/cyan]")
            if all_file_ids:
                console.print(f"[dim]使用文件: {len(uploaded_file_ids)}个上传文件, {len(intermediate_file_ids)}个中间文件[/dim]")

            # 默认流式响应
            console.print("[dim]📡 流式响应中...[/dim]")
            response_text = ""
            collected_files = []

            console.print("\n[bold yellow]🤖 AI回复:[/bold yellow]")

            stream_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                stream=True,
                extra_body={
                    "docs/analysis_depth": MAX_RECURSION_DEPTH,
                    "report_format": REPORT_FORMAT,
                    "report_language": REPORT_LANGUAGE,
                    "report_export_mode": REPORT_EXPORT_MODE,
                    "visual_style": VISUAL_STYLE,
                    "visual_interactive": VISUAL_INTERACTIVE,
                },
            )

            for chunk in stream_response:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        response_text += content
                        console.print(content, end='')

                    # 收集生成的文件（在流中）
                    if hasattr(chunk, 'generated_files') and chunk.generated_files:
                        collected_files.extend(chunk.generated_files)

            console.print()  # 换行

            # 添加AI回复到历史
            self.chat_history.append({"role": "assistant", "content": response_text})

            # 处理生成的文件
            if collected_files:
                console.print(f"\n[green]📁 生成了 {len(collected_files)} 个文件[/green]")

                intermediate_count = 0
                for file_info in collected_files:
                    file_name = file_info.get('name', '未知文件')
                    file_url = file_info.get('url', '')
                    file_id = file_info.get('id', '')

                    # 判断是否为中间文件
                    if self.is_intermediate_file(file_info):
                        # 上传中间文件
                        uploaded_id = self.upload_intermediate_file(file_info)
                        if uploaded_id:
                            intermediate_count += 1
                        # 仍保存到generated_files用于统计
                        self.generated_files.append({
                            **file_info,
                            'uploaded_id': uploaded_id,
                            'type': 'intermediate'
                        })
                    else:
                        # 报告和图片文件，直接保存
                        # 尝试从URL获取文件大小
                        file_size = file_info.get('size', '未知')
                        if file_size == '未知' and file_url:
                            try:
                                import requests
                                response = requests.head(file_url, timeout=5)
                                if response.status_code == 200 and 'content-length' in response.headers:
                                    size_bytes = int(response.headers['content-length'])
                                    file_size = decimal(size_bytes)
                                else:
                                    # 如果HEAD请求失败，尝试完整下载
                                    response = requests.get(file_url, timeout=10)
                                    if response.status_code == 200:
                                        size_bytes = len(response.content)
                                        file_size = decimal(size_bytes)
                            except Exception:
                                # 如果获取失败，保持为'未知'
                                pass

                        self.generated_files.append({
                            **file_info,
                            'type': 'output',
                            'size': file_size
                        })
                        console.print(f"[dim]• {file_name}: {file_url or file_id}[/dim]")

                if intermediate_count > 0:
                    console.print(f"[dim]✅ {intermediate_count}个文件已作为中间文件上传，可供后续对话使用[/dim]")

            return response_text

        except Exception as e:
            console.print(f"[red]❌ 对话错误: {e}[/red]")
            return None


    def delete_file_by_id(self, file_id: str):
        """根据ID删除文件"""
        try:
            if not self.client:
                if not self.initialize_client():
                    return False

            console.print(f"[yellow]🗑️  正在删除文件: {file_id}[/yellow]")
            self.client.files.delete(file_id)

            # 从本地列表中移除
            self.uploaded_files = [f for f in self.uploaded_files if f['id'] != file_id]
            console.print(f"[green]✅ 文件删除成功[/green]")
            return True

        except Exception as e:
            console.print(f"[red]❌ 删除文件失败: {e}[/red]")
            return False

    def download_file_by_id(self, file_id: str, save_path: str = None):
        """根据ID下载文件"""
        try:
            if not self.client:
                if not self.initialize_client():
                    return

            console.print(f"[cyan]📥 正在下载文件: {file_id}[/cyan]")
            file_content = self.client.files.content(file_id)

            # 确定保存路径
            file_info = next((f for f in self.uploaded_files if f['id'] == file_id), None)
            if file_info:
                filename = file_info['name']
            else:
                filename = f"downloaded_file_{file_id[:8]}"

            if save_path:
                save_path = Path(save_path)
                if save_path.is_dir():
                    save_path = save_path / filename
            else:
                save_path = Path(filename)

            # 写入文件
            with open(save_path, 'wb') as f:
                f.write(file_content.content)

            console.print(f"[green]✅ 文件下载成功: {save_path}[/green]")
            console.print(f"[dim]文件大小: {decimal(len(file_content.content))}[/dim]")

        except Exception as e:
            console.print(f"[red]❌ 下载文件失败: {e}[/red]")

    def show_history(self):
        """显示对话历史"""
        if not self.chat_history:
            console.print("[yellow]📝 暂无对话历史[/yellow]")
            return

        output_files = [f for f in self.generated_files if f.get('type') != 'intermediate']
        intermediate_files = [f for f in self.generated_files if f.get('type') == 'intermediate']

        console.print(Panel(
            f"[bold]对话轮数:[/bold] {len(self.chat_history) // 2}\n"
            f"[bold]用户消息:[/bold] {len([m for m in self.chat_history if m['role'] == 'user'])}\n"
            f"[bold]AI回复:[/bold] {len([m for m in self.chat_history if m['role'] == 'assistant'])}\n"
            f"[bold]输出文件:[/bold] {len(output_files)}\n"
            f"[bold]中间文件:[/bold] {len(intermediate_files)}",
            title="对话历史统计",
            border_style="blue"
        ))

        # 显示最近对话
        console.print("\n[bold]最近对话记录:[/bold]")
        recent_messages = self.chat_history[-6:]  # 显示最近6条消息

        for i, msg in enumerate(recent_messages):
            role_emoji = "👤" if msg['role'] == 'user' else "🤖"
            role_color = "blue" if msg['role'] == 'user' else "green"

            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            console.print(f"[{role_color}]{role_emoji} {msg['role'].title()}:[/{role_color}] {content}")

            if i < len(recent_messages) - 1:
                console.print()


    def clear_chat_history(self):
        """清除对话历史和生成的中间文件"""
        # 删除中间文件
        if self.intermediate_files:
            console.print("[yellow]🗑️  正在删除中间文件...[/yellow]")
            for file_info in self.intermediate_files:
                try:
                    self.client.files.delete(file_info['id'])
                    console.print(f"[green]✅ 已删除中间文件: {file_info['name']}[/green]")
                except Exception as e:
                    console.print(f"[red]❌ 删除中间文件失败 {file_info['name']}: {e}[/red]")

        # 清空本地列表
        self.chat_history.clear()
        self.generated_files.clear()
        self.intermediate_files.clear()

        console.print("[green]✅ 对话历史已清除[/green]")
        console.print("[green]✅ 生成文件记录已清除[/green]")
        console.print("[green]✅ 中间文件已删除[/green]")

    def clear_all(self):
        """清除所有内容（包括上传文件）"""
        try:
            # 删除服务器文件 - 包括上传文件和中间文件
            if self.uploaded_files:
                for file_info in self.uploaded_files:
                    try:
                        self.client.files.delete(file_info['id'])
                        console.print(f"[green]✅ 已删除上传文件: {file_info['name']}[/green]")
                    except Exception as e:
                        console.print(f"[red]❌ 删除上传文件失败 {file_info['name']}: {e}[/red]")

            if self.intermediate_files:
                for file_info in self.intermediate_files:
                    try:
                        self.client.files.delete(file_info['id'])
                        console.print(f"[green]✅ 已删除中间文件: {file_info['name']}[/green]")
                    except Exception as e:
                        console.print(f"[red]❌ 删除中间文件失败 {file_info['name']}: {e}[/red]")

            # 清空本地列表
            self.chat_history.clear()
            self.generated_files.clear()
            self.intermediate_files.clear()
            self.uploaded_files.clear()

            console.print("[green]✅ 所有内容已清除[/green]")
            console.print("[green]✅ 对话历史、生成文件、上传文件、中间文件全部清除[/green]")

        except Exception as e:
            console.print(f"[red]❌ 清除所有内容时出错: {e}[/red]")

    def get_system_status(self):
        """获取系统状态"""
        try:
            console.print("[cyan]🔍 正在获取系统状态...[/cyan]")

            # 服务器状态
            server_status = "✅ 在线" if self.check_server() else "❌ 离线"

            # 统计
            output_files = [f for f in self.generated_files if f.get('type') == 'output']
            status_panel = Panel(
                f"[bold]API服务器:[/bold] {server_status}\n"
                f"[bold]API端点:[/bold] {self.api_base}\n"
                f"[bold]当前模型:[/bold] {self.model}\n"
                f"[bold]上传文件:[/bold] {len(self.uploaded_files)}\n"
                f"[bold]中间文件:[/bold] {len(self.intermediate_files)}\n"
                f"[bold]输出文件:[/bold] {len(output_files)}\n"
                f"[bold]对话轮数:[/bold] {len([m for m in self.chat_history if m['role'] == 'user'])}",
                title="系统状态",
                border_style="cyan"
            )
            console.print(status_panel)

        except Exception as e:
            console.print(f"[red]❌ 获取系统状态失败: {e}[/red]")

    def interactive_mode(self):
        """交互式对话模式"""
        console.print("\n[bold green]💬 进入交互式对话模式[/bold green]")

        # 显示帮助信息
        self.show_help()

        while True:
            try:
                # 使用简单的输入提示，避免使用终端控制序列
                user_input = input("您: ").strip()

                # 每次有效输入后保存历史
                if user_input:
                    self.save_history()

                if user_input.lower() in ['quit', 'exit', '退出']:
                    console.print("[green]👋 再见![/green]")
                    break

                # 处理各种命令
                if self.handle_command(user_input):
                    continue

                if not user_input:
                    continue

                # 获取当前上传的文件ID
                file_ids = [f['id'] for f in self.uploaded_files]

                # 执行对话（默认流式输出）
                self.chat_with_file(user_input, file_ids if file_ids else None, stream=True)

            except KeyboardInterrupt:
                console.print("\n[green]👋 再见![/green]")
                break
            except EOFError:
                console.print("\n[green]👋 再见![/green]")
                break
            except Exception as e:
                console.print(f"[red]❌ 错误: {e}[/red]")

    def show_help(self):
        """显示帮助信息"""
        help_text = """
[bold cyan]📋 可用命令:[/bold cyan]

[基本命令]
• [yellow]help[/yellow] - 显示此帮助信息
• [yellow]quit/exit/退出[/yellow] - 退出程序
• [yellow]clear[/yellow] - 清除对话历史和生成的中间文件
• [yellow]clear-all[/yellow] - 清除所有内容（包括上传文件）

[文件管理]
• [yellow]files[/yellow] - 查看上传文件
• [yellow]upload <file_path>[/yellow] - 上传新文件
• [yellow]delete <file_id>[/yellow] - 删除指定文件
• [yellow]download <file_id> [save_path][/yellow] - 下载文件

[系统 & 历史]
• [yellow]status[/yellow] - 显示系统状态
• [yellow]history[/yellow] - 显示对话历史
• [yellow]fid[/yellow] - 显示所有文件名和完整ID

[dim]直接输入文本即可开始对话，系统会自动使用上传和生成的文件[/dim]
"""
        console.print(Panel(help_text, title="命令帮助", border_style="blue"))

    def handle_command(self, user_input: str) -> bool:
        """处理命令，如果是命令返回True"""
        cmd = user_input.lower().strip()

        # 帮助命令
        if cmd in ['help', 'h', '帮助']:
            self.show_help()
            return True

        # 清除对话历史
        elif cmd in ['clear', '清除']:
            if Confirm.ask("确定要清除对话历史和生成的中间文件吗？"):
                self.clear_chat_history()
            return True

        # 清除所有内容
        elif cmd in ['clear-all', '全部清除']:
            if Confirm.ask("确定要清除所有内容吗？这将删除所有上传文件"):
                self.clear_all()
            return True

        # 文件管理命令
        elif cmd in ['files', 'ls', '文件']:
            self.list_uploaded_files()
            return True

        elif cmd.startswith('upload '):
            file_path = user_input[7:].strip()
            if file_path:
                self.upload_file(file_path)
            return True

        elif cmd.startswith('delete '):
            file_id = user_input[7:].strip()
            if file_id:
                self.delete_file_by_id(file_id)
            return True

        elif cmd.startswith('download '):
            parts = user_input.split()
            if len(parts) >= 2:
                file_id = parts[1]
                save_path = parts[2] if len(parts) > 2 else None
                self.download_file_by_id(file_id, save_path)
            return True

        # 系统命令
        elif cmd in ['status', '状态']:
            self.get_system_status()
            return True

        # 历史命令
        elif cmd in ['history', '历史']:
            self.show_history()
            return True

        # 文件ID命令
        elif cmd in ['fid']:
            self.show_file_ids()
            return True

        # 不是命令
        return False

    def show_file_ids(self):
        """显示所有文件名和完整ID（包括上传文件和中间文件）"""
        # 检查是否有任何文件
        if not self.uploaded_files and not self.intermediate_files:
            console.print("[yellow]📝 暂无文件[/yellow]")
            return

        # 创建综合表格
        table = Table(title="所有文件和ID", show_header=True, header_style="bold magenta")
        table.add_column("文件名", style="cyan", no_wrap=True)
        table.add_column("完整文件ID", style="green")
        table.add_column("类型", style="yellow")
        table.add_column("状态", style="blue")

        # 显示上传文件
        if self.uploaded_files:
            for file_info in self.uploaded_files:
                table.add_row(
                    file_info['name'],
                    file_info['id'],  # 完整ID
                    "📁 用户上传",
                    "✅ 已上传"
                )

        # 显示中间文件
        if self.intermediate_files:
            for file_info in self.intermediate_files:
                table.add_row(
                    file_info['name'],
                    file_info['id'],  # 完整ID
                    "🔄 中间文件",
                    "🔄 AI生成"
                )

        console.print(table)

        # 显示摘要
        console.print()
        console.print(f"[dim]总文件数: {len(self.uploaded_files) + len(self.intermediate_files)}[/dim]")
        console.print(f"[dim]用户上传: {len(self.uploaded_files)}[/dim]")
        console.print(f"[dim]中间文件: {len(self.intermediate_files)}[/dim]")

    def cleanup_files(self):
        """清理上传文件"""
        if not self.uploaded_files:
            return

        if not self.client:
            self.initialize_client()

        console.print("[yellow]🧹 正在清理上传文件...[/yellow]")

        for file_info in self.uploaded_files:
            try:
                # 使用OpenAI库删除文件
                self.client.files.delete(file_info['id'])
                console.print(f"[green]✅ 已删除: {file_info['name']}[/green]")
            except Exception as e:
                console.print(f"[red]❌ 删除错误 {file_info['name']}: {e}[/red]")

        # 清空本地列表
        self.uploaded_files.clear()

    def run(self):
        """运行主程序 - 直接进入交互模式"""
        try:
            # 检查服务器状态
            if not self.check_server():
                console.print("[red]❌ API服务器未运行![/red]")
                console.print("[yellow]请先启动API服务器: python backend/main.py[/yellow]")
                return

            self.display_header()
            console.print("[green]✅ API服务器连接成功[/green]")
            console.print(f"[dim]当前模型: {self.model}[/dim]")
            console.print(f"[dim]API端点: {self.api_base}[/dim]\n")

            # 直接进入交互模式
            self.interactive_mode()

        except KeyboardInterrupt:
            console.print("\n[green]👋 程序终止[/green]")
            self.cleanup_files()
        except Exception as e:
            console.print(f"[red]❌ 程序错误: {e}[/red]")
            self.cleanup_files()


def main():
    """主函数"""
    cli = DeepAnalyzeCLI()
    cli.run()


if __name__ == "__main__":
    main()
