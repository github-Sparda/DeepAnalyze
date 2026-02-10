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
            report_dir = self.data_sessions_active_base / session_id / "reports" / report_id
            report_dir.mkdir(parents=True, exist_ok=True)
            
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
            metadata_file.write_text(json.dumps(metadata_dict, ensure_ascii=False, indent=2), encoding="utf-8")
            
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
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.FILESYSTEM,
                context={"session_id": session_id, "title": title}
            )
            raise e
    
    def get_report(self, session_id: str, report_id: str) -> Optional[Dict[str, Any]]:
        """获取报告"""
        try:
            report_dir = self.data_sessions_active_base / session_id / "reports" / report_id
            if not report_dir.exists():
                return None
            
            # 读取元数据
            metadata_file = report_dir / "metadata.json"
            if not metadata_file.exists():
                return None
            
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            
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
        """导出为PDF（简化版本，实际需要weasyprint）"""
        # 这里是简化实现，实际项目中需要集成PDF生成库
        pdf_content = f"""
# {metadata['title']}

**作者:** {metadata['author']}  
**创建时间:** {metadata['created_at']}  
**报告类型:** {metadata['report_type']}

---

{content}
        """
        Path(output_path).write_text(pdf_content, encoding="utf-8")
        return output_path
    
    def _export_to_markdown(self, content: str, metadata: Dict[str, Any], output_path: str) -> str:
        """导出为Markdown"""
        md_content = f"""# {metadata['title']}

**作者:** {metadata['author']}  
**创建时间:** {metadata['created_at']}  
**报告类型:** {metadata['report_type']}

---

{content}
        """
        Path(output_path).write_text(md_content, encoding="utf-8")
        return output_path
    
    def _export_to_docx(self, content: str, metadata: Dict[str, Any], output_path: str) -> str:
        """导出为DOCX（简化版本）"""
        # 实际项目中需要使用python-docx库
        docx_content = f"""
{metadata['title']}

作者: {metadata['author']}
创建时间: {metadata['created_at']}
报告类型: {metadata['report_type']}

{content}
        """
        Path(output_path).write_text(docx_content, encoding="utf-8")
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
        """简单的Markdown转HTML（简化版本）"""
        # 这里是极简实现，实际项目中应该使用markdown库
        html = markdown_text.replace('\n\n', '</p><p>')
        html = html.replace('# ', '<h1>').replace('\n', '<br>')
        return f"<p>{html}</p>"


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
