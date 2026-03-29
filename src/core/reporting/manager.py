"""
Enhanced Report Generation and Management System
增强版报告生成和管理系统
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import hashlib

from ..error.handler import ErrorHandler, ErrorSeverity, ErrorCategory
from ..state.manager import get_session_state, update_session_state
from ..common import ensure_dir, save_json, load_json, error_handling_context


class ReportType(Enum):
    """报告类型"""
    ANALYTICAL = "analytical"      # 分析报告
    TECHNICAL = "technical"        # 技术报告
    EXECUTIVE = "executive"        # 执行报告
    RESEARCH = "research"          # 研究报告
    SUMMARY = "summary"            # 摘要报告


class ReportStatus(Enum):
    """报告状态"""
    DRAFT = "draft"                # 草稿
    REVIEW = "review"              # 审核中
    APPROVED = "approved"          # 已批准
    PUBLISHED = "published"        # 已发布
    ARCHIVED = "data_sessions_archivedd"          # 已归档


class ExportFormat(Enum):
    """导出格式"""
    HTML = "html"
    PDF = "pdf"
    MARKDOWN = "markdown"
    DOCX = "docx"
    LATEX = "latex"
    JSON = "json"


@dataclass
class ReportMetadata:
    """报告元数据"""
    report_id: str
    title: str
    author: str
    created_at: datetime
    updated_at: datetime
    report_type: ReportType
    status: ReportStatus
    version: str
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    word_count: int = 0
    page_count: int = 0


@dataclass
class ReportVersion:
    """报告版本"""
    version: str
    content: str
    created_at: datetime
    author: str
    changes: List[str] = field(default_factory=list)
    checksum: str = ""


@dataclass
class ReportTemplate:
    """报告模板"""
    template_id: str
    name: str
    description: str
    report_type: ReportType
    sections: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    style_config: Dict[str, Any] = field(default_factory=dict)


class ReportManager:
    """报告管理器"""
    
    def __init__(self, data_sessions_active_base: str = "data_sessions_active"):
        self.data_sessions_active_base = Path(data_sessions_active_base)
        self.error_handler = ErrorHandler()
        self.default_templates = self._load_default_templates()
    
    def _load_default_templates(self) -> Dict[str, ReportTemplate]:
        """加载默认模板"""
        return {
            "analytical": ReportTemplate(
                template_id="analytical",
                name="分析报告模板",
                description="标准数据分析报告模板",
                report_type=ReportType.ANALYTICAL,
                sections=["摘要", "数据概览", "分析方法", "主要发现", "结论建议"],
                variables={
                    "company_name": "公司名称",
                    "docs_analysis_period": "分析期间",
                    "analyst_name": "分析师姓名"
                }
            ),
            "executive": ReportTemplate(
                template_id="executive",
                name="执行报告模板",
                description="高层管理决策报告模板",
                report_type=ReportType.EXECUTIVE,
                sections=["执行摘要", "关键指标", "业务洞察", "风险评估", "行动建议"],
                variables={
                    "quarter": "季度",
                    "year": "年份",
                    "department": "部门"
                }
            )
        }
    
    def create_report(
        self,
        session_id: str,
        title: str,
        content: str,
        report_type: ReportType = ReportType.ANALYTICAL,
        template_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReportMetadata:
        """创建新报告"""
        try:
            # 生成报告ID
            report_id = f"report_{int(time.time())}_{hash(title) % 10000:04d}"
            
            # 获取模板
            template = self.default_templates.get(template_id or "analytical")
            
            # 创建报告目录
            report_dir = ensure_dir(self.data_sessions_active_base / session_id / "reports" / report_id)

            # 保存报告内容
            content_file = report_dir / "content.md"
            content_file.write_text(content, encoding="utf-8")

            # 创建元数据
            report_metadata = ReportMetadata(
                report_id=report_id,
                title=title,
                author=metadata.get("author", "DeepAnalyze") if metadata else "DeepAnalyze",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                report_type=report_type,
                status=ReportStatus.DRAFT,
                version="1.0",
                tags=metadata.get("tags", []) if metadata else [],
                keywords=metadata.get("keywords", []) if metadata else [],
                data_sources=metadata.get("data_sources", []) if metadata else [],
                word_count=len(content.split()),
                page_count=max(1, len(content) // 2000)  # 粗略估算页数
            )

            # 保存元数据
            metadata_file = report_dir / "metadata.json"
            metadata_dict = {
                "report_id": report_metadata.report_id,
                "title": report_metadata.title,
                "author": report_metadata.author,
                "created_at": report_metadata.created_at.isoformat(),
                "updated_at": report_metadata.updated_at.isoformat(),
                "report_type": report_metadata.report_type.value,
                "status": report_metadata.status.value,
                "version": report_metadata.version,
                "tags": report_metadata.tags,
                "keywords": report_metadata.keywords,
                "data_sources": report_metadata.data_sources,
                "word_count": report_metadata.word_count,
                "page_count": report_metadata.page_count
            }
            save_json(metadata_file, metadata_dict)
            
            # 更新会话状态
            state_updates = {
                f"report_{report_id}": {
                    "metadata": metadata_dict,
                    "content_path": str(content_file),
                    "template_used": template.template_id if template else None
                }
            }
            update_session_state(session_id, state_updates)

            return report_metadata

        except Exception:
            with error_handling_context(
                self.error_handler,
                severity="high",
                category="filesystem",
                context={"session_id": session_id, "title": title}
            ):
                raise
    
    def get_report(self, session_id: str, report_id: str) -> Optional[Dict[str, Any]]:
        """获取报告"""
        try:
            report_dir = self.data_sessions_active_base / session_id / "reports" / report_id
            if not report_dir.exists():
                return None
            
            # 读取元数据
            metadata_file = report_dir / "metadata.json"
            metadata = load_json(metadata_file)
            if not metadata:
                return None
            
            # 读取内容
            content_file = report_dir / "content.md"
            content = content_file.read_text(encoding="utf-8") if content_file.exists() else ""
            
            return {
                "metadata": metadata,
                "content": content,
                "report_dir": str(report_dir)
            }
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.FILESYSTEM,
                context={"session_id": session_id, "report_id": report_id}
            )
            return None
    
    def list_reports(self, session_id: str) -> List[ReportMetadata]:
        """列出会话中的所有报告"""
        try:
            reports_dir = self.data_sessions_active_base / session_id / "reports"
            if not reports_dir.exists():
                return []
            
            reports = []
            for report_dir in reports_dir.iterdir():
                if report_dir.is_dir():
                    metadata_file = report_dir / "metadata.json"
                    if metadata_file.exists():
                        try:
                            metadata_dict = json.loads(metadata_file.read_text(encoding="utf-8"))
                            metadata = ReportMetadata(
                                report_id=metadata_dict["report_id"],
                                title=metadata_dict["title"],
                                author=metadata_dict["author"],
                                created_at=datetime.fromisoformat(metadata_dict["created_at"]),
                                updated_at=datetime.fromisoformat(metadata_dict["updated_at"]),
                                report_type=ReportType(metadata_dict["report_type"]),
                                status=ReportStatus(metadata_dict["status"]),
                                version=metadata_dict["version"],
                                tags=metadata_dict.get("tags", []),
                                keywords=metadata_dict.get("keywords", []),
                                data_sources=metadata_dict.get("data_sources", []),
                                word_count=metadata_dict.get("word_count", 0),
                                page_count=metadata_dict.get("page_count", 0)
                            )
                            reports.append(metadata)
                        except Exception:
                            continue
            
            # 按创建时间排序
            reports.sort(key=lambda x: x.created_at, reverse=True)
            return reports
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.FILESYSTEM,
                context={"session_id": session_id}
            )
            return []
    
    def update_report(
        self, 
        session_id: str, 
        report_id: str, 
        content: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """更新报告"""
        try:
            report = self.get_report(session_id, report_id)
            if not report:
                return False
            
            report_dir = Path(report["report_dir"])
            
            # 更新内容
            if content is not None:
                content_file = report_dir / "content.md"
                content_file.write_text(content, encoding="utf-8")
                
                # 更新元数据中的统计信息
                if metadata_updates is None:
                    metadata_updates = {}
                metadata_updates["word_count"] = len(content.split())
                metadata_updates["page_count"] = max(1, len(content) // 2000)
            
            # 更新元数据
            if metadata_updates:
                metadata_file = report_dir / "metadata.json"
                current_metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                
                # 更新字段
                for key, value in metadata_updates.items():
                    if key in current_metadata:
                        current_metadata[key] = value
                
                current_metadata["updated_at"] = datetime.now().isoformat()
                
                # 保存更新后的元数据
                metadata_file.write_text(
                    json.dumps(current_metadata, ensure_ascii=False, indent=2), 
                    encoding="utf-8"
                )
                
                # 更新会话状态
                state_updates = {f"report_{report_id}": {"metadata": current_metadata}}
                update_session_state(session_id, state_updates)
            
            return True
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.FILESYSTEM,
                context={"session_id": session_id, "report_id": report_id}
            )
            return False
    
    def delete_report(self, session_id: str, report_id: str) -> bool:
        """删除报告"""
        try:
            report_dir = self.data_sessions_active_base / session_id / "reports" / report_id
            if report_dir.exists():
                import shutil
                shutil.rmtree(report_dir)
                
                # 更新会话状态
                state = get_session_state(session_id)
                if state and f"report_{report_id}" in state:
                    state_updates = {f"report_{report_id}": None}
                    update_session_state(session_id, state_updates)
                
                return True
            return False
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.FILESYSTEM,
                context={"session_id": session_id, "report_id": report_id}
            )
            return False
    
    def export_report(
        self,
        session_id: str,
        report_id: str,
        format: ExportFormat,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """导出报告"""
        try:
            report = self.get_report(session_id, report_id)
            if not report:
                return None
            
            content = report["content"]
            metadata = report["metadata"]
            
            # 确定输出路径
            if output_path is None:
                output_dir = self.data_sessions_active_base / session_id / "exports"
                output_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{metadata['title']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format.value}"
                output_path = str(output_dir / filename)
            
            # 根据格式导出
            if format == ExportFormat.HTML:
                return self._export_to_html(content, metadata, output_path)
            elif format == ExportFormat.PDF:
                return self._export_to_pdf(content, metadata, output_path)
            elif format == ExportFormat.MARKDOWN:
                return self._export_to_markdown(content, metadata, output_path)
            elif format == ExportFormat.DOCX:
                return self._export_to_docx(content, metadata, output_path)
            elif format == ExportFormat.JSON:
                return self._export_to_json(content, metadata, output_path)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
                
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.EXECUTION,
                context={"session_id": session_id, "report_id": report_id, "format": format.value}
            )
            return None
    
    def _export_to_html(self, content: str, metadata: Dict[str, Any], output_path: str) -> str:
        """导出为HTML"""
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{metadata['title']}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; line-height: 1.6; }}
        header {{ border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #34495e; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        .metadata {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .section {{ margin: 25px 0; }}
    </style>
</head>
<body>
    <header>
        <h1>{metadata['title']}</h1>
        <div class="metadata">
            <p><strong>作者:</strong> {metadata['author']}</p>
            <p><strong>创建时间:</strong> {metadata['created_at']}</p>
            <p><strong>报告类型:</strong> {metadata['report_type']}</p>
        </div>
    </header>
    <div class="content">
        {self._markdown_to_html(content)}
    </div>
</body>
</html>
        """
        
        Path(output_path).write_text(html_template, encoding="utf-8")
        return output_path
    
    def _export_to_pdf(self, content: str, metadata: Dict[str, Any], output_path: str) -> str:
        """导出为PDF（使用weasyprint）"""
        try:
            from weasyprint import HTML

            # 构建HTML内容
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{metadata.get('title', 'Report')}</title>
    <style>
        @page {{
            size: A4;
            margin: 2.5cm;
            @top-center {{ content: "{metadata.get('title', 'Report')}"; font-size: 9pt; color: #666; }}
            @bottom-center {{ content: "Page " counter(page); font-size: 9pt; }}
        }}
        body {{
            font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 5px;
            margin-top: 30px;
        }}
        h3 {{ color: #7f8c8d; margin-top: 20px; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        pre {{
            background-color: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        blockquote {{
            border-left: 4px solid #3498db;
            margin: 0;
            padding-left: 15px;
            color: #666;
        }}
        .metadata {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="metadata">
        <h1>{metadata.get('title', 'Report')}</h1>
        <p><strong>作者:</strong> {metadata.get('author', 'Unknown')}</p>
        <p><strong>创建时间:</strong> {metadata.get('created_at', 'N/A')}</p>
        <p><strong>报告类型:</strong> {metadata.get('report_type', 'N/A')}</p>
    </div>
    <hr>
    {content}
</body>
</html>"""

            HTML(string=html_content).write_pdf(output_path)
            return output_path
        except ImportError:
            # weasyprint 未安装，生成一个说明文件
            fallback_content = f"""# PDF Export Not Available

## 原因
weasyprint 库未安装。要启用PDF导出功能，请运行：
```bash
pip install weasyprint
```

## 报告内容

# {metadata.get('title', 'Report')}

**作者:** {metadata.get('author', 'Unknown')}  
**创建时间:** {metadata.get('created_at', 'N/A')}  
**报告类型:** {metadata.get('report_type', 'N/A')}

---

{content}
"""
            # 保存为markdown格式，但使用.pdf扩展名以提示用户
            output_path = str(output_path).replace('.pdf', '.md')
            Path(output_path).write_text(fallback_content, encoding="utf-8")
            return output_path
    
    def _export_to_markdown(self, content: str, metadata: Dict[str, Any], output_path: str) -> str:
        """导出为Markdown（带YAML Front Matter）"""
        import yaml

        # 构建YAML Front Matter
        front_matter = {
            "title": metadata.get('title', 'Untitled'),
            "author": metadata.get('author', 'Unknown'),
            "date": metadata.get('created_at', 'N/A'),
            "report_type": metadata.get('report_type', 'N/A'),
            "tags": metadata.get('tags', []),
            "keywords": metadata.get('keywords', []),
            "version": metadata.get('version', '1.0'),
        }

        # 构建完整的Markdown内容
        md_content = f"""---
{yaml.dump(front_matter, allow_unicode=True, sort_keys=False)}---

# {metadata.get('title', 'Untitled')}

<div class="metadata">

**作者:** {metadata.get('author', 'Unknown')}  
**创建时间:** {metadata.get('created_at', 'N/A')}  
**报告类型:** {metadata.get('report_type', 'N/A')}

</div>

---

{content}

---

*Generated by DeepAnalyze*
"""
        Path(output_path).write_text(md_content, encoding="utf-8")
        return output_path
    
    def _export_to_docx(self, content: str, metadata: Dict[str, Any], output_path: str) -> str:
        """导出为DOCX（使用python-docx）"""
        try:
            from docx import Document
            from docx.shared import Inches, Pt, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            import re

            doc = Document()

            # 添加标题
            title = doc.add_heading(metadata.get('title', 'Report'), 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # 添加元数据
            doc.add_paragraph(f"作者: {metadata.get('author', 'Unknown')}")
            doc.add_paragraph(f"创建时间: {metadata.get('created_at', 'N/A')}")
            doc.add_paragraph(f"报告类型: {metadata.get('report_type', 'N/A')}")
            doc.add_paragraph()  # 空行

            # 解析Markdown内容并转换为DOCX
            lines = content.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]

                # 处理标题
                if line.startswith('# '):
                    doc.add_heading(line[2:], level=1)
                elif line.startswith('## '):
                    doc.add_heading(line[3:], level=2)
                elif line.startswith('### '):
                    doc.add_heading(line[4:], level=3)
                elif line.startswith('#### '):
                    doc.add_heading(line[5:], level=4)
                # 处理列表
                elif line.startswith('- ') or line.startswith('* '):
                    doc.add_paragraph(line[2:], style='List Bullet')
                elif re.match(r'^\d+\.\s', line):
                    doc.add_paragraph(re.sub(r'^\d+\.\s', '', line), style='List Number')
                # 处理代码块
                elif line.startswith('```'):
                    code_lines = []
                    i += 1
                    while i < len(lines) and not lines[i].startswith('```'):
                        code_lines.append(lines[i])
                        i += 1
                    if code_lines:
                        code_para = doc.add_paragraph()
                        code_run = code_para.add_run('\n'.join(code_lines))
                        code_run.font.name = 'Courier New'
                        code_run.font.size = Pt(9)
                # 处理普通段落
                elif line.strip():
                    # 处理粗体和斜体
                    para = doc.add_paragraph()
                    parts = re.split(r'(\*\*.*?\*\*|\*.*?\*)', line)
                    for part in parts:
                        if part.startswith('**') and part.endswith('**'):
                            run = para.add_run(part[2:-2])
                            run.bold = True
                        elif part.startswith('*') and part.endswith('*'):
                            run = para.add_run(part[1:-1])
                            run.italic = True
                        else:
                            para.add_run(part)
                else:
                    # 空行
                    doc.add_paragraph()

                i += 1

            # 添加页脚
            section = doc.sections[0]
            footer = section.footer
            footer_para = footer.paragraphs[0]
            footer_para.text = f"Generated by DeepAnalyze | {metadata.get('title', 'Report')}"

            doc.save(output_path)
            return output_path

        except ImportError:
            # python-docx 未安装，生成一个说明文件
            fallback_content = f"""# DOCX Export Not Available

## 原因
python-docx 库未安装。要启用DOCX导出功能，请运行：
```bash
pip install python-docx
```

## 报告内容

# {metadata.get('title', 'Report')}

**作者:** {metadata.get('author', 'Unknown')}  
**创建时间:** {metadata.get('created_at', 'N/A')}  
**报告类型:** {metadata.get('report_type', 'N/A')}

---

{content}
"""
            # 保存为markdown格式
            output_path = str(output_path).replace('.docx', '.md')
            Path(output_path).write_text(fallback_content, encoding="utf-8")
            return output_path
    
    def _export_to_json(self, content: str, metadata: Dict[str, Any], output_path: str) -> str:
        """导出为JSON"""
        export_data = {
            "metadata": metadata,
            "content": content,
            "exported_at": datetime.now().isoformat()
        }
        Path(output_path).write_text(
            json.dumps(export_data, ensure_ascii=False, indent=2), 
            encoding="utf-8"
        )
        return output_path
    
    def _markdown_to_html(self, markdown_text: str) -> str:
        """将Markdown文本转换为HTML"""
        import markdown
        _MD_EXTENSIONS = [
            "tables",
            "fenced_code",
            "codehilite",
            "nl2br",
            "sane_lists",
        ]
        _MD_EXTENSION_CONFIGS = {
            "codehilite": {"css_class": "highlight", "guess_lang": False},
            "tables": {},
            "fenced_code": {},
            "nl2br": {},
            "sane_lists": {},
        }
        html = markdown.markdown(
            markdown_text,
            extensions=_MD_EXTENSIONS,
            extension_configs=_MD_EXTENSION_CONFIGS,
            output_format="html",
        )
        return html


# 便捷函数
def get_report_manager(data_sessions_active_base: str = "data_sessions_active") -> ReportManager:
    """获取报告管理器实例"""
    return ReportManager(data_sessions_active_base)


def create_new_report(
    session_id: str,
    title: str,
    content: str,
    report_type: ReportType = ReportType.ANALYTICAL,
    template_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> ReportMetadata:
    """便捷函数：创建新报告"""
    manager = get_report_manager()
    return manager.create_report(session_id, title, content, report_type, template_id, metadata)


def list_session_reports(session_id: str) -> List[ReportMetadata]:
    """便捷函数：列出会话报告"""
    manager = get_report_manager()
    return manager.list_reports(session_id)
