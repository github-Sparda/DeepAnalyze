#!/usr/bin/env python3
"""
进度跟踪和WebSocket系统集成测试
"""

import sys
import os
import time
import threading

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 直接导入需要的模块，避免API包的复杂依赖
from src.api.progress_tracker import create_task, start_task, update_progress, complete_task, get_task_progress
from src.api.websocket_handler import start_websocket_server, stop_websocket_server, notify_progress, notify_task_status

def run_analysis_simulation():
    """模拟数据分析过程"""
    print('=== 开始数据分析模拟 ===')
    
    # 创建主任务
    main_task = create_task('完整数据分析流程')
    print(f'创建任务ID: {main_task}')
    
    start_task(main_task)
    notify_task_status(main_task, 'running', '开始完整数据分析流程')
    
    # 分析阶段
    stages = [
        ('数据加载', 0.2),
        ('数据清洗', 0.4),
        ('统计分析', 0.7),
        ('可视化生成', 0.9),
        ('报告生成', 1.0)
    ]
    
    for stage_name, target_progress in stages:
        print(f'\n--- {stage_name} ---')
        notify_progress(main_task, {
            'progress': target_progress - 0.1,
            'message': f'正在执行: {stage_name}',
            'stage': stage_name
        })
        
        # 模拟该阶段的工作
        for i in range(5):
            progress = target_progress - 0.1 + (i * 0.02)
            update_progress(main_task, progress, f'{stage_name} - 步骤 {i+1}/5')
            notify_progress(main_task, {
                'progress': progress,
                'message': f'{stage_name} - 步骤 {i+1}/5',
                'detail': f'处理中...'
            })
            time.sleep(0.3)
        
        # 阶段完成
        update_progress(main_task, target_progress, f'{stage_name} 完成')
        notify_progress(main_task, {
            'progress': target_progress,
            'message': f'✅ {stage_name} 完成',
            'stage_complete': True
        })
        print(f'{stage_name} 完成')
    
    # 任务完成
    complete_task(main_task, '数据分析全流程完成')
    notify_task_status(main_task, 'completed', '🎉 数据分析成功完成!')
    
    print(f'\n=== 分析完成 ===')
    final_status = get_task_progress(main_task)
    print(f'最终进度: {final_status.progress:.0%}')
    print(f'事件总数: {len(final_status.events)}')
    print(f'任务ID: {main_task}')
    print(f'WebSocket地址: ws://localhost:8765/progress/{main_task}')
    
    return main_task

def main():
    """主函数"""
    print('🚀 启动进度跟踪和WebSocket测试系统')
    print('=' * 50)
    
    # 启动WebSocket服务器
    print('🔌 启动WebSocket服务器...')
    if start_websocket_server(8765):
        print('✅ WebSocket服务器启动成功')
        print('🌐 服务器地址: ws://localhost:8765')
    else:
        print('❌ WebSocket服务器启动失败')
        return
    
    print('\n📝 测试说明:')
    print('1. 使用任意 WebSocket 客户端连接 ws://localhost:8765')
    print('2. 连接路径使用 /progress/<任务ID> (任务ID下方会显示)')
    print('3. 观察实时进度更新')
    print('=' * 50)
    
    # 运行分析模拟
    try:
        task_id = run_analysis_simulation()
        
        print(f'\n🎯 测试任务ID: {task_id}')
        print('💡 请在测试页面中使用此ID连接')
        
        # 保持服务器运行一段时间以便测试
        print('\n⏳ 服务器将继续运行30秒供测试...')
        time.sleep(30)
        
    except KeyboardInterrupt:
        print('\n⏹️  收到中断信号')
    except Exception as e:
        print(f'\n❌ 运行错误: {e}')
    finally:
        print('\n🔌 正在停止WebSocket服务器...')
        stop_websocket_server()
        print('✅ 服务器已停止')

if __name__ == '__main__':
    main()
