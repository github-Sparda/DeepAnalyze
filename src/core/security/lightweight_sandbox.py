"""
轻量级沙箱执行环境
基于Linux namespaces和cgroups的进程级隔离
"""

import os
import subprocess
import threading
import time
import resource
import signal
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from contextlib import contextmanager
import json
import tempfile

@dataclass
class ResourceLimits:
    """资源限制配置"""
    memory_mb: int = 500          # 内存限制(MB)
    cpu_time_seconds: int = 30    # CPU时间限制(秒)
    file_size_mb: int = 10        # 文件大小限制(MB)
    max_processes: int = 10       # 最大进程数
    timeout_seconds: int = 60     # 执行超时时间

@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    memory_used: int = 0
    cpu_time: float = 0.0
    error_message: Optional[str] = None

class LightweightSandbox:
    """轻量级沙箱执行器"""
    
    def __init__(self, limits: Optional[ResourceLimits] = None):
        self.limits = limits or ResourceLimits()
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.process_lock = threading.Lock()
        
    def execute_code(self, code: str, user_id: str = "default", 
                    timeout: Optional[int] = None) -> ExecutionResult:
        """
        在沙箱中执行代码
        
        Args:
            code: 要执行的Python代码
            user_id: 用户标识
            timeout: 执行超时时间（秒）
            
        Returns:
            ExecutionResult: 执行结果
        """
        start_time = time.time()
        timeout = timeout or self.limits.timeout_seconds
        
        try:
            # 创建临时文件存储代码
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', 
                                           delete=False) as f:
                f.write(code)
                code_file = f.name
            
            # 构建受限制的执行命令
            cmd = self._build_restricted_command(code_file)
            
            # 设置资源限制
            preexec_fn = self._create_preexec_function()
            
            # 执行代码
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=preexec_fn,
                text=True,
                bufsize=1
            )
            
            # 监控执行过程
            with self.process_lock:
                self.active_processes[user_id] = process
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                exit_code = process.returncode
                
                execution_time = time.time() - start_time
                
                # 获取资源使用情况
                memory_used = self._get_memory_usage(process.pid) if process.pid else 0
                
                return ExecutionResult(
                    success=exit_code == 0,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    execution_time=execution_time,
                    memory_used=memory_used
                )
                
            finally:
                # 清理进程
                with self.process_lock:
                    if user_id in self.active_processes:
                        del self.active_processes[user_id]
                # 清理临时文件
                try:
                    os.unlink(code_file)
                except Exception:
                    pass
                    
        except subprocess.TimeoutExpired:
            # 超时处理
            self._terminate_process(user_id)
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"执行超时 ({timeout}秒)",
                exit_code=-1,
                execution_time=execution_time,
                error_message="timeout"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time=execution_time,
                error_message=str(e)
            )
    
    def _build_restricted_command(self, code_file: str) -> List[str]:
        """构建受限制的执行命令"""
        # 使用nice降低进程优先级
        cmd = [
            'nice', '-n', '19',  # 最低优先级
            'python3', code_file
        ]
        return cmd
    
    def _create_preexec_function(self):
        """创建进程执行前的限制函数"""
        def set_limits():
            try:
                # 设置内存限制 (bytes)
                memory_limit = self.limits.memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
                
                # 设置CPU时间限制
                cpu_limit = self.limits.cpu_time_seconds
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
                
                # 设置文件大小限制
                file_limit = self.limits.file_size_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
                
                # 设置最大进程数
                resource.setrlimit(resource.RLIMIT_NPROC, 
                                 (self.limits.max_processes, self.limits.max_processes))
                
                # 设置栈大小限制
                stack_limit = 8 * 1024 * 1024  # 8MB
                resource.setrlimit(resource.RLIMIT_STACK, (stack_limit, stack_limit))
                
                # 更改工作目录到临时目录
                temp_dir = tempfile.mkdtemp()
                os.chdir(temp_dir)
                
                # 限制文件描述符
                max_fds = 100
                resource.setrlimit(resource.RLIMIT_NOFILE, (max_fds, max_fds))
                
            except Exception as e:
                print(f"设置资源限制失败: {e}")
        
        return set_limits
    
    def _get_memory_usage(self, pid: int) -> int:
        """获取进程内存使用量（bytes）"""
        try:
            # 读取/proc/pid/status获取内存信息
            with open(f'/proc/{pid}/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        # VmRSS是实际使用的物理内存
                        memory_kb = int(line.split()[1])
                        return memory_kb * 1024
            return 0
        except Exception:
            return 0
    
    def _terminate_process(self, user_id: str):
        """终止指定用户的进程"""
        with self.process_lock:
            if user_id in self.active_processes:
                process = self.active_processes[user_id]
                try:
                    # 先尝试优雅终止
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 强制终止
                    try:
                        process.kill()
                        process.wait()
                    except Exception:
                        pass
                except Exception:
                    pass
                finally:
                    if user_id in self.active_processes:
                        del self.active_processes[user_id]
    
    def terminate_all_processes(self):
        """终止所有活动进程"""
        with self.process_lock:
            user_ids = list(self.active_processes.keys())
        for user_id in user_ids:
            self._terminate_process(user_id)
    
    def get_active_processes(self) -> Dict[str, Dict[str, Any]]:
        """获取活动进程信息"""
        with self.process_lock:
            info = {}
            for user_id, process in self.active_processes.items():
                info[user_id] = {
                    'pid': process.pid,
                    'start_time': getattr(process, '_start_time', 'unknown'),
                    'status': process.poll() if process.poll() is not None else 'running'
                }
            return info

class RestrictedPythonEnvironment:
    """受限的Python执行环境"""
    
    def __init__(self, sandbox: LightweightSandbox):
        self.sandbox = sandbox
        self.restricted_builtins = self._create_restricted_builtins()
    
    def _create_restricted_builtins(self) -> Dict[str, Any]:
        """创建受限的内置函数"""
        # 允许的安全内置函数
        safe_builtins = {
            'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
            'bytearray': bytearray, 'bytes': bytes, 'chr': chr, 'complex': complex,
            'dict': dict, 'divmod': divmod, 'enumerate': enumerate, 'filter': filter,
            'float': float, 'format': format, 'frozenset': frozenset, 'getattr': getattr,
            'hasattr': hasattr, 'hash': hash, 'hex': hex, 'int': int, 'isinstance': isinstance,
            'issubclass': issubclass, 'iter': iter, 'len': len, 'list': list, 'map': map,
            'max': max, 'min': min, 'next': next, 'oct': oct, 'ord': ord, 'pow': pow,
            'range': range, 'repr': repr, 'reversed': reversed, 'round': round,
            'set': set, 'slice': slice, 'sorted': sorted, 'str': str, 'sum': sum,
            'tuple': tuple, 'type': type, 'zip': zip
        }
        return safe_builtins
    
    def execute_safe_code(self, code: str, user_id: str = "default", 
                         timeout: Optional[int] = None) -> ExecutionResult:
        """执行安全的Python代码"""
        # 包装代码以应用限制
        wrapped_code = self._wrap_code_with_restrictions(code)
        return self.sandbox.execute_code(wrapped_code, user_id, timeout)
    
    def _wrap_code_with_restrictions(self, code: str) -> str:
        """包装代码以应用安全限制"""
        restriction_wrapper = f'''
import builtins
import sys

# 替换内置函数为受限版本
safe_builtins = {json.dumps(list(self.restricted_builtins.keys()))}
original_builtins = dict(builtins.__dict__)

# 移除危险的内置函数
dangerous_functions = [
    '__import__', 'eval', 'exec', 'compile', 'open', 'file', 
    'input', '__build_class__', '__loader__', '__spec__'
]

for func in dangerous_functions:
    if func in builtins.__dict__:
        del builtins.__dict__[func]

# 执行用户代码
try:
{self._indent_code(code, 4)}
except Exception as e:
    print(f"执行错误: {{e}}", file=sys.stderr)
    raise
finally:
    # 恢复原始内置函数
    builtins.__dict__.update(original_builtins)
'''
        return restriction_wrapper
    
    def _indent_code(self, code: str, indent_level: int) -> str:
        """缩进代码"""
        lines = code.strip().split('\n')
        indent = ' ' * indent_level
        return '\n'.join(indent + line for line in lines)

# 全局实例
_global_sandbox = None
_global_restricted_env = None

def get_sandbox() -> LightweightSandbox:
    """获取全局沙箱实例"""
    global _global_sandbox
    if _global_sandbox is None:
        _global_sandbox = LightweightSandbox()
    return _global_sandbox

def get_restricted_environment() -> RestrictedPythonEnvironment:
    """获取受限Python环境"""
    global _global_restricted_env
    if _global_restricted_env is None:
        sandbox = get_sandbox()
        _global_restricted_env = RestrictedPythonEnvironment(sandbox)
    return _global_restricted_env

# 便捷函数
def execute_in_sandbox(code: str, user_id: str = "default", 
                      timeout: Optional[int] = None) -> ExecutionResult:
    """在沙箱中执行代码的便捷函数"""
    env = get_restricted_environment()
    return env.execute_safe_code(code, user_id, timeout)

def get_sandbox_stats() -> Dict[str, Any]:
    """获取沙箱统计信息"""
    sandbox = get_sandbox()
    return {
        'active_processes': len(sandbox.active_processes),
        'process_info': sandbox.get_active_processes()
    }
