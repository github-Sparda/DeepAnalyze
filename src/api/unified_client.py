"""
Unified API Client for DeepAnalyze
Provides a consistent interface for all API interactions
"""

import os
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import json

from openai import OpenAI
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import (
    API_BASE,
    DEEPANALYZE_VLLM_API_KEY,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    HTTP_SERVER_BASE,
    MAX_NEW_TOKENS,
)


class UnifiedAPIClient:
    """统一的API客户端，封装所有外部服务调用"""
    
    def __init__(self):
        """初始化API客户端"""
        # 初始化OpenAI兼容客户端
        self.openai_client = OpenAI(
            base_url=API_BASE,
            api_key=DEEPANALYZE_VLLM_API_KEY,
        )
        
        # 配置默认参数
        self.default_model = DEFAULT_MODEL
        self.default_temperature = DEFAULT_TEMPERATURE
        self.max_tokens = MAX_NEW_TOKENS
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Union[str, Any]:
        """
        统一的聊天补全接口
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式返回
            
        Returns:
            完整响应或流式响应对象
        """
        try:
            response = self.openai_client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                temperature=temperature or self.default_temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=stream
            )
            
            if stream:
                return response
            else:
                return response.choices[0].message.content or ""
                
        except Exception as e:
            raise Exception(f"Chat completion failed: {str(e)}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def upload_file(
        self,
        file_path: Union[str, Path],
        purpose: str = "file-extract"
    ) -> Dict[str, Any]:
        """
        上传文件到API服务
        
        Args:
            file_path: 文件路径
            purpose: 文件用途
            
        Returns:
            文件对象信息
        """
        try:
            with open(file_path, 'rb') as f:
                file_obj = self.openai_client.files.create(
                    file=f,
                    purpose=purpose
                )
            return file_obj.dict()
        except Exception as e:
            raise Exception(f"File upload failed: {str(e)}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def download_file(self, file_url: str, save_path: Union[str, Path]) -> bool:
        """
        从文件服务下载文件
        
        Args:
            file_url: 文件URL
            save_path: 保存路径
            
        Returns:
            下载是否成功
        """
        try:
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            raise Exception(f"File download failed: {str(e)}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def list_files(self, purpose: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出文件
        
        Args:
            purpose: 文件用途过滤
            
        Returns:
            文件列表
        """
        try:
            files = self.openai_client.files.list(purpose=purpose)
            return [file.dict() for file in files.data]
        except Exception as e:
            raise Exception(f"List files failed: {str(e)}")
    
    def prepare_messages(
        self,
        instruction: str,
        file_ids: Optional[List[str]] = None,
        data_sessions_active_files: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        准备标准化的消息格式
        
        Args:
            instruction: 用户指令
            file_ids: 文件ID列表
            data_sessions_active_files: 工作区文件信息
            
        Returns:
            格式化后的消息列表
        """
        content_parts = [f"# Instruction\n{instruction}"]
        
        if data_sessions_active_files:
            file_info = "\n".join([
                f"File {i+1}: {{\"name\": \"{f.get('name', 'unknown')}\", \"size\": \"{f.get('size', 'unknown')}\"}}"
                for i, f in enumerate(data_sessions_active_files)
            ])
            content_parts.append(f"\n# Data\n{file_info}")
        
        messages = [{"role": "user", "content": "\n".join(content_parts)}]
        
        if file_ids:
            messages[0]["file_ids"] = file_ids
            
        return messages


# 全局客户端实例
api_client = UnifiedAPIClient()


def get_api_client() -> UnifiedAPIClient:
    """获取全局API客户端实例"""
    return api_client
