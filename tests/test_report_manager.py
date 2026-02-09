"""
Enhanced Report System Tests and Examples
增强版报告系统测试和示例
"""

from reporting.manager import (
    ReportManager,
    ReportType,
    ReportStatus,
    ExportFormat,
    create_new_report,
    list_session_reports
)
import time


def demo_report_creation():
    """演示报告创建功能"""
    print("=== 报告创建功能演示 ===")
    
    manager = ReportManager()
    session_id = "report_demo_session"
    
    # 创建示例报告内容
    sample_content = """
# 销售数据分析报告

## 摘要
本报告分析了2024年第一季度的销售数据，涵盖了主要产品的销售表现和市场趋势。

## 数据概览
- 总销售额：¥1,250,000
- 订单数量：1,250笔
- 平均订单价值：¥1,000
- 客户数量：890人

## 主要发现
1. **产品表现**：A产品贡献了45%的销售额
2. **地域分析**：华东地区销售额增长25%
3. **时间趋势**：月度销售额呈现稳步上升趋势
4. **客户分析**：回头客占比达到68%

## 结论与建议
- 建议加大对A产品的营销投入
- 华东地区市场潜力巨大，值得重点开发
- 需要加强客户关系管理，提高客户留存率
"""
    
    # 创建报告
    metadata = create_new_report(
        session_id=session_id,
        title="2024年Q1销售数据分析报告",
        content=sample_content,
        report_type=ReportType.ANALYTICAL,
        temporarylate_id="analytical",
        metadata={
            "author": "数据分析团队",
            "tags": ["销售", "分析", "季度报告"],
            "keywords": ["销售额", "客户", "产品"],
            "data_sources": ["sales_database_2024_q1"]
        }
    )
    
    print(f"创建报告成功:")
    print(f"  报告ID: {metadata.report_id}")
    print(f"  标题: {metadata.title}")
    print(f"  类型: {metadata.report_type.value}")
    print(f"  状态: {metadata.status.value}")
    print(f"  字数: {metadata.word_count}")
    print(f"  页数: {metadata.page_count}")
    
    return metadata.report_id


def demo_report_management(report_id: str):
    """演示报告管理功能"""
    print("\n=== 报告管理功能演示 ===")
    
    manager = ReportManager()
    session_id = "report_demo_session"
    
    # 获取报告
    report = manager.get_report(session_id, report_id)
    if report:
        print(f"获取报告成功:")
        print(f"  标题: {report['metadata']['title']}")
        print(f"  作者: {report['metadata']['author']}")
        print(f"  内容长度: {len(report['content'])} 字符")
    
    # 列出所有报告
    reports = list_session_reports(session_id)
    print(f"\n会话中报告总数: {len(reports)}")
    for report_meta in reports[:3]:  # 显示前3个
        print(f"  - {report_meta.title} ({report_meta.report_type.value})")
    
    # 更新报告
    update_success = manager.update_report(
        session_id,
        report_id,
        metadata_updates={
            "status": ReportStatus.REVIEW.value,
            "tags": ["销售", "分析", "季度报告", "已审核"]
        }
    )
    print(f"\n报告更新: {'成功' if update_success else '失败'}")
    
    # 验证更新
    updated_report = manager.get_report(session_id, report_id)
    if updated_report:
        print(f"更新后状态: {updated_report['metadata']['status']}")
        print(f"更新后标签: {updated_report['metadata']['tags']}")


def demo_report_export(report_id: str):
    """演示报告导出功能"""
    print("\n=== 报告导出功能演示 ===")
    
    manager = ReportManager()
    session_id = "report_demo_session"
    
    # 导出为不同格式
    export_formats = [
        (ExportFormat.HTML, "HTML格式"),
        (ExportFormat.MARKDOWN, "Markdown格式"),
        (ExportFormat.JSON, "JSON格式")
    ]
    
    for format_type, format_name in export_formats:
        try:
            export_path = manager.export_report(
                session_id,
                report_id,
                format_type
            )
            if export_path:
                print(f"{format_name}导出成功: {export_path}")
            else:
                print(f"{format_name}导出失败")
        except Exception as e:
            print(f"{format_name}导出异常: {e}")


def demo_temporarylate_system():
    """演示模板系统"""
    print("\n=== 模板系统演示 ===")
    
    manager = ReportManager()
    
    print("可用模板:")
    for temporarylate_id, template in manager.default_temporarylates.items():
        print(f"  {temporarylate_id}: {template.name}")
        print(f"    描述: {template.description}")
        print(f"    类型: {template.report_type.value}")
        print(f"    章节: {', '.join(template.sections)}")
        print()


def demo_error_handling():
    """演示错误处理功能"""
    print("\n=== 错误处理演示 ===")
    
    manager = ReportManager()
    session_id = "error_test_session"
    
    # 测试不存在的报告
    non_existent = manager.get_report(session_id, "non_existent_report")
    print(f"获取不存在报告: {'成功' if non_existent else '失败（正确）'}")
    
    # 测试无效的会话
    reports = list_session_reports("invalid_session")
    print(f"无效会话报告列表: {len(reports)} 项（正确为空）")
    
    # 测试报告删除
    delete_success = manager.delete_report(session_id, "non_existent_report")
    print(f"删除不存在报告: {'成功' if delete_success else '失败（正确）'}")


def performance_test():
    """性能测试"""
    print("\n=== 性能测试 ===")
    
    import time
    
    manager = ReportManager()
    session_id = f"perf_test_{int(time.time())}"
    
    # 创建大量报告测试性能
    start_time = time.time()
    
    for i in range(10):
        content = f"# 测试报告 {i+1}\n\n这是第{i+1}个测试报告的内容。" * 10
        metadata = create_new_report(
            session_id,
            f"性能测试报告 {i+1}",
            content,
            ReportType.SUMMARY
        )
    
    creation_time = time.time() - start_time
    
    # 列出报告
    list_start = time.time()
    reports = list_session_reports(session_id)
    list_time = time.time() - list_start
    
    print(f"创建10个报告耗时: {creation_time:.3f}秒")
    print(f"列出报告耗时: {list_time:.3f}秒")
    print(f"平均每报告创建时间: {creation_time_10:.3f}秒")
    print(f"报告总数: {len(reports)}")


if __name__ == "__main__":
    print("DeepAnalyze 增强版报告系统演示")
    print("=" * 50)
    
    try:
        # 执行所有演示
        report_id = demo_report_creation()
        demo_report_management(report_id)
        demo_report_export(report_id)
        demo_temporarylate_system()
        demo_error_handling()
        performance_test()
        
        print("\n" + "=" * 50)
        print("🎉 所有演示完成！")
        print("\n增强版报告系统特点:")
        print("✅ 完整的报告生命周期管理")
        print("✅ 多种报告类型和模板支持")
        print("✅ 丰富的元数据和版本控制")
        print("✅ 多格式导出功能")
        print("✅ 完善的错误处理机制")
        print("✅ 性能优化的存储和检索")
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()