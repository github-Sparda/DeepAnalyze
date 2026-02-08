"""
WebSocket实时推送功能
提供进度更新的实时推送服务
"""

import asyncio
import json
import time
import threading
from typing import Dict, List, Set, Callable, Optional, Any
import weakref

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("警告: websockets库未安装，WebSocket功能不可用")

class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.connections: Dict[str, weakref.WeakSet] = {}
        self.connection_lock = threading.RLock()
        self.running = False
        self.server = None
        self.port = 8765
        
    def add_connection(self, channel: str, websocket):
        """添加WebSocket连接"""
        with self.connection_lock:
            if channel not in self.connections:
                self.connections[channel] = weakref.WeakSet()
            self.connections[channel].add(websocket)
            
    def remove_connection(self, channel: str, websocket):
        """移除WebSocket连接"""
        with self.connection_lock:
            if channel in self.connections:
                self.connections[channel].discard(websocket)
                if not self.connections[channel]:
                    del self.connections[channel]
    
    def get_connections(self, channel: str) -> List:
        """获取指定频道的连接"""
        with self.connection_lock:
            if channel in self.connections:
                # 清理已断开的连接
                active_connections = [conn for conn in self.connections[channel] 
                                    if not conn.closed]
                self.connections[channel] = weakref.WeakSet(active_connections)
                return active_connections
            return []
    
    def broadcast_message(self, channel: str, message: Dict[str, Any]) -> int:
        """广播消息到指定频道"""
        if not WEBSOCKETS_AVAILABLE:
            return 0
            
        connections = self.get_connections(channel)
        if not connections:
            return 0
        
        message_str = json.dumps(message, ensure_ascii=False)
        successful_sends = 0
        
        # 异步发送消息
        async def send_to_connections():
            tasks = []
            for conn in connections:
                if not conn.closed:
                    tasks.append(asyncio.create_task(conn.send(message_str)))
            
            if tasks:
                try:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    return len(tasks)
                except Exception:
                    return 0
            return 0
        
        # 在事件循环中执行
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，在新线程中执行
                def run_send():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result = new_loop.run_until_complete(send_to_connections())
                        return result
                    finally:
                        new_loop.close()
                
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_send)
                    successful_sends = future.result(timeout=5)
            else:
                successful_sends = loop.run_until_complete(send_to_connections())
        except Exception as e:
            print(f"消息广播错误: {e}")
        
        return successful_sends
    
    async def handle_client(self, websocket, path: str):
        """处理客户端连接"""
        # 从路径提取频道名，例如 "/progress/task_123"
        if path.startswith('/'):
            path = path[1:]
        
        channel = path or "default"
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        
        print(f"WebSocket客户端连接: {client_id} -> 频道: {channel}")
        
        try:
            # 添加连接
            self.add_connection(channel, websocket)
            
            # 发送欢迎消息
            welcome_msg = {
                "type": "welcome",
                "channel": channel,
                "timestamp": time.time(),
                "message": f"已连接到频道 {channel}"
            }
            await websocket.send(json.dumps(welcome_msg, ensure_ascii=False))
            
            # 保持连接活跃
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # 处理客户端消息
                    response = self._handle_client_message(channel, data)
                    if response:
                        await websocket.send(json.dumps(response, ensure_ascii=False))
                except json.JSONDecodeError:
                    error_msg = {
                        "type": "error",
                        "message": "无效的JSON格式"
                    }
                    await websocket.send(json.dumps(error_msg, ensure_ascii=False))
                except Exception as e:
                    error_msg = {
                        "type": "error",
                        "message": f"处理消息时出错: {str(e)}"
                    }
                    await websocket.send(json.dumps(error_msg, ensure_ascii=False))
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"WebSocket连接关闭: {client_id}")
        except Exception as e:
            print(f"WebSocket处理错误: {e}")
        finally:
            # 移除连接
            self.remove_connection(channel, websocket)
            print(f"WebSocket客户端断开: {client_id}")
    
    def _handle_client_message(self, channel: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理客户端消息"""
        msg_type = data.get('type', '')
        
        if msg_type == 'ping':
            return {
                "type": "pong",
                "timestamp": time.time()
            }
        elif msg_type == 'subscribe':
            # 订阅特定事件类型
            event_types = data.get('event_types', [])
            return {
                "type": "subscription_confirmed",
                "event_types": event_types,
                "timestamp": time.time()
            }
        else:
            return {
                "type": "unknown_message_type",
                "received_type": msg_type
            }
    
    def start_server(self, port: int = 8765):
        """启动WebSocket服务器"""
        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError("websockets库未安装，无法启动WebSocket服务器")
        
        if self.running:
            return
        
        self.port = port
        self.running = True
        
        async def server_coroutine():
            self.server = await websockets.serve(
                self.handle_client,
                "localhost",
                port
            )
            print(f"WebSocket服务器启动在 ws://localhost:{port}")
            await self.server.wait_closed()
        
        # 在新线程中运行事件循环
        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(server_coroutine())
            finally:
                loop.close()
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
    
    def stop_server(self):
        """停止WebSocket服务器"""
        if not self.running:
            return
        
        self.running = False
        if self.server:
            self.server.close()
        
        print("WebSocket服务器已停止")

class ProgressWebSocketNotifier:
    """进度WebSocket通知器"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.ws_manager = websocket_manager
        self.notification_handlers: List[Callable] = []
    
    def notify_progress_update(self, task_id: str, progress_data: Dict[str, Any]):
        """通知进度更新"""
        message = {
            "type": "progress_update",
            "task_id": task_id,
            "data": progress_data,
            "timestamp": time.time()
        }
        
        # 发送到任务特定频道
        channel = f"progress/{task_id}"
        sent_count = self.ws_manager.broadcast_message(channel, message)
        
        # 发送到通用进度频道
        general_sent = self.ws_manager.broadcast_message("progress", message)
        
        # 调用自定义处理函数
        for handler in self.notification_handlers:
            try:
                handler(task_id, progress_data, message)
            except Exception as e:
                print(f"通知处理函数错误: {e}")
        
        return sent_count + general_sent
    
    def notify_task_status(self, task_id: str, status: str, message: str = ""):
        """通知任务状态变化"""
        notification = {
            "type": "task_status",
            "task_id": task_id,
            "status": status,
            "message": message,
            "timestamp": time.time()
        }
        
        channel = f"progress/{task_id}"
        sent_count = self.ws_manager.broadcast_message(channel, notification)
        general_sent = self.ws_manager.broadcast_message("progress", notification)
        
        return sent_count + general_sent
    
    def add_notification_handler(self, handler: Callable[[str, Dict, Dict], None]):
        """添加自定义通知处理函数"""
        self.notification_handlers.append(handler)
    
    def remove_notification_handler(self, handler: Callable) -> bool:
        """移除通知处理函数"""
        try:
            self.notification_handlers.remove(handler)
            return True
        except ValueError:
            return False

# 全局实例
_global_ws_manager = None
_global_notifier = None

def get_websocket_manager() -> WebSocketManager:
    """获取全局WebSocket管理器"""
    global _global_ws_manager
    if _global_ws_manager is None:
        _global_ws_manager = WebSocketManager()
    return _global_ws_manager

def get_progress_notifier() -> ProgressWebSocketNotifier:
    """获取进度通知器"""
    global _global_notifier
    if _global_notifier is None:
        ws_manager = get_websocket_manager()
        _global_notifier = ProgressWebSocketNotifier(ws_manager)
    return _global_notifier

# 便捷函数
def start_websocket_server(port: int = 8765):
    """启动WebSocket服务器"""
    if not WEBSOCKETS_AVAILABLE:
        print("警告: websockets库未安装，WebSocket服务器无法启动")
        print("请运行: pip install websockets")
        return False
    
    try:
        manager = get_websocket_manager()
        manager.start_server(port)
        return True
    except Exception as e:
        print(f"启动WebSocket服务器失败: {e}")
        return False

def stop_websocket_server():
    """停止WebSocket服务器"""
    manager = get_websocket_manager()
    manager.stop_server()

def notify_progress(task_id: str, progress_data: Dict[str, Any]) -> int:
    """发送进度通知"""
    notifier = get_progress_notifier()
    return notifier.notify_progress_update(task_id, progress_data)

def notify_task_status(task_id: str, status: str, message: str = "") -> int:
    """发送任务状态通知"""
    notifier = get_progress_notifier()
    return notifier.notify_task_status(task_id, status, message)