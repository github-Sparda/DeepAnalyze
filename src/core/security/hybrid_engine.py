"""
混合安全执行引擎
结合轻量级沙箱和容器池的优势，提供智能的安全执行环境
"""

import time
import threading
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass

from .lightweight_sandbox import get_sandbox, get_restricted_environment, ExecutionResult
from .container_pool import get_container_pool

class SecurityLevel(Enum):
    """安全级别"""
    SANDBOX = "sandbox"      # 轻量级沙箱 - 最低开销
    CONTAINER = "container"  # 容器隔离 - 中等开销  
    STRICT = "strict"        # 严格隔离 - 最高安全性

@dataclass
class UserTrustProfile:
    """用户信任档案"""
    user_id: str
    trust_level: int = 1      # 1-10, 10为最高信任
    execution_count: int = 0  # 执行次数
    violation_count: int = 0  # 违规次数
    last_execution: float = 0 # 最后执行时间

class TrustEvaluator:
    """信任评估器"""
    
    def __init__(self):
        self.user_profiles: Dict[str, UserTrustProfile] = {}
        self.lock = threading.Lock()
    
    def evaluate_user(self, user_id: str, execution_result: ExecutionResult) -> int:
        """评估用户信任等级"""
        with self.lock:
            if user_id not in self.user_profiles:
                self.user_profiles[user_id] = UserTrustProfile(user_id)
            
            profile = self.user_profiles[user_id]
            profile.execution_count += 1
            profile.last_execution = time.time()
            
            # 根据执行结果调整信任等级
            if not execution_result.success:
                if "timeout" in (execution_result.error_message or ""):
                    profile.violation_count += 1
                elif "memory" in (execution_result.stderr or "").lower():
                    profile.violation_count += 1
            
            # 计算信任分数
            base_score = profile.trust_level
            execution_bonus = min(profile.execution_count // 10, 3)  # 每10次执行+1分，最多+3
            violation_penalty = profile.violation_count * 2  # 每次违规-2分
            
            trust_score = max(1, min(10, base_score + execution_bonus - violation_penalty))
            profile.trust_level = trust_score
            
            return trust_score
    
    def get_user_profile(self, user_id: str) -> Optional[UserTrustProfile]:
        """获取用户档案"""
        with self.lock:
            return self.user_profiles.get(user_id)
    
    def get_security_level(self, user_id: str, requested_level: Optional[SecurityLevel] = None) -> SecurityLevel:
        """根据用户档案确定安全级别"""
        profile = self.get_user_profile(user_id)
        
        if requested_level:
            return requested_level
        
        if not profile:
            return SecurityLevel.SANDBOX  # 新用户默认沙箱
        
        if profile.trust_level >= 8:
            return SecurityLevel.SANDBOX  # 高信任用户用沙箱
        elif profile.trust_level >= 5:
            return SecurityLevel.CONTAINER  # 中等信任用户用容器
        else:
            return SecurityLevel.STRICT  # 低信任用户用严格模式

class HybridSecurityEngine:
    """混合安全执行引擎"""
    
    def __init__(self, default_limits: Optional[Dict] = None):
        self.trust_evaluator = TrustEvaluator()
        self.sandbox = get_sandbox()
        self.container_pool = get_container_pool()
        self.default_limits = default_limits or {}
        
        # 执行统计
        self.execution_stats = {
            'sandbox_executions': 0,
            'container_executions': 0,
            'strict_executions': 0,
            'total_executions': 0
        }
        self.stats_lock = threading.Lock()
    
    def execute_code(self, 
                    code: str, 
                    user_id: str,
                    security_level: Optional[SecurityLevel] = None,
                    timeout: Optional[int] = None,
                    custom_limits: Optional[Dict] = None) -> Dict[str, Any]:
        """
        智能执行代码
        
        Args:
            code: 要执行的代码
            user_id: 用户ID
            security_level: 指定的安全级别
            timeout: 执行超时时间
            custom_limits: 自定义资源限制
            
        Returns:
            执行结果字典
        """
        start_time = time.time()
        
        # 确定安全级别
        actual_level = self.trust_evaluator.get_security_level(user_id, security_level)
        
        # 应用自定义限制
        execution_limits = self.default_limits.copy()
        if custom_limits:
            execution_limits.update(custom_limits)
        
        execution_timeout = timeout or execution_limits.get('timeout', 30)
        
        try:
            # 根据安全级别选择执行方式
            if actual_level == SecurityLevel.SANDBOX:
                result = self._execute_in_sandbox(code, user_id, execution_timeout)
                self._update_stats('sandbox_executions')
                
            elif actual_level == SecurityLevel.CONTAINER:
                result = self._execute_in_container(code, user_id, execution_timeout)
                self._update_stats('container_executions')
                
            else:  # STRICT
                result = self._execute_in_strict_mode(code, user_id, execution_timeout)
                self._update_stats('strict_executions')
            
            # 评估用户信任
            execution_result = ExecutionResult(
                success=result['success'],
                stdout=result['stdout'],
                stderr=result['stderr'],
                exit_code=result['exit_code'],
                execution_time=time.time() - start_time,
                error_message=result.get('error_message')
            )
            
            trust_score = self.trust_evaluator.evaluate_user(user_id, execution_result)
            
            # 添加执行信息
            result.update({
                'security_level': actual_level.value,
                'trust_score': trust_score,
                'execution_time': time.time() - start_time,
                'timestamp': time.time()
            })
            
            self._update_stats('total_executions')
            return result
            
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'exit_code': -1,
                'error_message': str(e),
                'security_level': actual_level.value if 'actual_level' in locals() else 'unknown',
                'execution_time': time.time() - start_time,
                'timestamp': time.time()
            }
    
    def _execute_in_sandbox(self, code: str, user_id: str, timeout: int) -> Dict[str, Any]:
        """在沙箱中执行"""
        try:
            result = self.sandbox.execute_code(code, user_id, timeout)
            return {
                'success': result.success,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exit_code': result.exit_code,
                'memory_used': result.memory_used,
                'error_message': result.error_message
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'exit_code': -1,
                'error_message': str(e)
            }
    
    def _execute_in_container(self, code: str, user_id: str, timeout: int) -> Dict[str, Any]:
        """在容器中执行"""
        try:
            result = self.container_pool.execute_in_session(user_id, code, timeout)
            return result
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'exit_code': -1,
                'error_message': str(e)
            }
    
    def _execute_in_strict_mode(self, code: str, user_id: str, timeout: int) -> Dict[str, Any]:
        """在严格模式下执行（创建独立容器）"""
        try:
            # 这里可以实现更严格的隔离，比如创建一次性容器
            # 为简化，暂时使用容器池的严格配置
            result = self.container_pool.execute_in_session(user_id, code, timeout)
            return result
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'exit_code': -1,
                'error_message': str(e)
            }
    
    def _update_stats(self, stat_name: str):
        """更新执行统计"""
        with self.stats_lock:
            self.execution_stats[stat_name] += 1
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        with self.stats_lock:
            stats = self.execution_stats.copy()
        
        # 计算百分比
        total = stats['total_executions']
        if total > 0:
            stats['sandbox_percentage'] = (stats['sandbox_executions'] / total) * 100
            stats['container_percentage'] = (stats['container_executions'] / total) * 100
            stats['strict_percentage'] = (stats['strict_executions'] / total) * 100
        
        # 添加用户统计
        user_stats = {
            'total_users': len(self.trust_evaluator.user_profiles),
            'high_trust_users': len([p for p in self.trust_evaluator.user_profiles.values() if p.trust_level >= 8]),
            'medium_trust_users': len([p for p in self.trust_evaluator.user_profiles.values() if 5 <= p.trust_level < 8]),
            'low_trust_users': len([p for p in self.trust_evaluator.user_profiles.values() if p.trust_level < 5])
        }
        
        stats.update(user_stats)
        return stats
    
    def get_user_trust_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信任信息"""
        profile = self.trust_evaluator.get_user_profile(user_id)
        if not profile:
            return None
        
        return {
            'user_id': profile.user_id,
            'trust_level': profile.trust_level,
            'execution_count': profile.execution_count,
            'violation_count': profile.violation_count,
            'last_execution': profile.last_execution,
            'security_level': self.trust_evaluator.get_security_level(user_id).value
        }
    
    def reset_user_trust(self, user_id: str):
        """重置用户信任等级"""
        with self.trust_evaluator.lock:
            if user_id in self.trust_evaluator.user_profiles:
                del self.trust_evaluator.user_profiles[user_id]

# 全局混合安全引擎实例
_global_security_engine = None

def get_security_engine() -> HybridSecurityEngine:
    """获取全局安全引擎实例"""
    global _global_security_engine
    if _global_security_engine is None:
        _global_security_engine = HybridSecurityEngine()
    return _global_security_engine

# 便捷函数
def secure_execute(code: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """安全执行代码的便捷函数"""
    engine = get_security_engine()
    return engine.execute_code(code, user_id, **kwargs)

def get_security_stats() -> Dict[str, Any]:
    """获取安全执行统计"""
    engine = get_security_engine()
    return engine.get_execution_statistics()

def get_user_trust(user_id: str) -> Optional[Dict[str, Any]]:
    """获取用户信任信息"""
    engine = get_security_engine()
    return engine.get_user_trust_info(user_id)