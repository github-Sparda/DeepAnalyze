#!/usr/bin/env python3
"""
Session Manager - 符合OpenSpec规范的会话和输出路径管理
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class SessionManager:
    """管理分析会话和输出路径"""
    
    def __init__(self, base_dir: str = "data/sessions/active"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.plans_dir = self.base_dir / "plans"
        self.artifacts_dir = self.base_dir / "artifacts"
        self.documents_dir = self.base_dir / "documents"
        
        # 确保所有目录存在
        for directory in [self.plans_dir, self.artifacts_dir, self.documents_dir]:
            directory.mkdir(exist_ok=True)
    
    def generate_plan_id(self) -> str:
        """生成唯一的plan_id"""
        return str(uuid.uuid4())[:8]
    
    def create_plan_record(self, data_source: str, hypotheses: list, validation_steps: list) -> str:
        """创建假设计划记录"""
        plan_id = self.generate_plan_id()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plan_filename = f"{timestamp}-{plan_id}-plan.json"
        plan_path = self.plans_dir / plan_filename
        
        plan_record = {
            "plan_id": plan_id,
            "timestamp": timestamp,
            "data_source": data_source,
            "hypothesis_list": hypotheses,
            "validation_steps": validation_steps,
            "expected_outputs": [],
            "status": "created"
        }
        
        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump(plan_record, f, indent=2, ensure_ascii=False)
        
        return plan_id
    
    def get_plan_path(self, plan_id: str) -> Optional[Path]:
        """获取指定plan_id的计划文件路径"""
        for plan_file in self.plans_dir.glob(f"*-{plan_id}-plan.json"):
            return plan_file
        return None
    
    def create_artifact_directory(self, plan_id: str, role: str) -> Path:
        """为特定角色创建产物目录"""
        artifact_dir = self.artifacts_dir / plan_id / role
        artifact_dir.mkdir(parents=True, exist_ok=True)
        return artifact_dir
    
    def register_artifact(self, plan_id: str, role: str, filename: str, artifact_type: str) -> Path:
        """注册产物并返回完整路径"""
        artifact_dir = self.create_artifact_directory(plan_id, role)
        artifact_path = artifact_dir / filename
        
        # 更新文档清单
        self._update_document_manifest(plan_id, role, filename, artifact_type, str(artifact_path))
        
        return artifact_path
    
    def _update_document_manifest(self, plan_id: str, role: str, filename: str, artifact_type: str, filepath: str):
        """更新文档清单"""
        manifest_path = self.documents_dir / "manifest.json"
        
        # 读取现有清单
        if manifest_path.exists():
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        else:
            manifest = {}
        
        # 更新或创建plan_id条目
        if plan_id not in manifest:
            manifest[plan_id] = {
                "artifacts": [],
                "created_at": datetime.now().isoformat()
            }
        
        # 添加新的产物记录
        artifact_record = {
            "role": role,
            "filename": filename,
            "type": artifact_type,
            "filepath": filepath,
            "timestamp": datetime.now().isoformat()
        }
        
        manifest[plan_id]["artifacts"].append(artifact_record)
        
        # 保存更新后的清单
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    def get_session_structure(self) -> Dict[str, Any]:
        """获取当前会话结构信息"""
        return {
            "base_directory": str(self.base_dir),
            "plans_directory": str(self.plans_dir),
            "artifacts_directory": str(self.artifacts_dir),
            "documents_directory": str(self.documents_dir),
            "plan_count": len(list(self.plans_dir.glob("*.json"))),
            "artifact_plans": len([d for d in self.artifacts_dir.iterdir() if d.is_dir()])
        }

# 全局会话管理器实例
session_manager = SessionManager()

if __name__ == "__main__":
    # 测试会话管理器
    sm = SessionManager()
    print("Session Manager initialized")
    print(f"Structure: {sm.get_session_structure()}")
    
    # 创建测试计划
    test_plan_id = sm.create_plan_record(
        data_source="test_data.csv",
        hypotheses=["数据分布呈现正态分布", "变量间存在相关性"],
        validation_steps=["计算描述性统计", "绘制分布图"]
    )
    print(f"Created test plan: {test_plan_id}")
    
    # 注册测试产物
    test_artifact = sm.register_artifact(test_plan_id, "analysis", "test_report.html", "report")
    print(f"Registered artifact: {test_artifact}")