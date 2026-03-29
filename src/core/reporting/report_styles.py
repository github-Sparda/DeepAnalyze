"""
报告样式模块

提供报告HTML渲染所需的CSS样式和JavaScript交互功能。
"""

REPORT_CSS = """
/* ===== 基础样式 ===== */
.report-container {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 14px;
    line-height: 1.7;
    color: #333;
    max-width: 1000px;
    margin: 0 auto;
    padding: 20px 30px;
    background: #fff;
}

/* ===== 标题层级样式 ===== */
.report-container h1 {
    font-size: 1.8em;
    font-weight: 700;
    color: #1a365d;
    border-bottom: 3px solid #3182ce;
    padding-bottom: 12px;
    margin-top: 0;
    margin-bottom: 20px;
}
.report-container h2 {
    font-size: 1.4em;
    font-weight: 700;
    color: #1e40af;
    border-bottom: 3px solid #3b82f6;
    padding-bottom: 8px;
    margin-top: 16px;
    margin-bottom: 12px;
}
.report-container h3 {
    font-size: 1.2em;
    font-weight: 600;
    color: #1e293b;
    margin-top: 12px;
    margin-bottom: 8px;
}
.report-container h4 {
    font-size: 1.1em;
    font-weight: 600;
    color: #475569;
    margin-top: 10px;
    margin-bottom: 6px;
}
.report-container h5 {
    font-size: 1em;
    font-weight: 600;
    color: #334155;
    margin-top: 8px;
    margin-bottom: 4px;
}

.report-container h2 {
    font-size: 1.4em;
    font-weight: 600;
    color: #2c5282;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 8px;
    margin-top: 32px;
    margin-bottom: 16px;
    cursor: pointer;
    user-select: none;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.report-container h2::before {
    content: "▼";
    font-size: 0.7em;
    margin-right: 10px;
    color: #718096;
    transition: transform 0.2s;
}

.report-container h2.collapsed::before {
    transform: rotate(-90deg);
}

.report-container h3 {
    font-size: 1.15em;
    font-weight: 600;
    color: #2d3748;
    margin-top: 24px;
    margin-bottom: 12px;
    padding-left: 12px;
    border-left: 4px solid #4299e1;
}

.report-container h4 {
    font-size: 1em;
    font-weight: 600;
    color: #4a5568;
    margin-top: 18px;
    margin-bottom: 8px;
}

/* ===== 折叠功能 ===== */
.report-container .section-content {
    overflow: hidden;
    transition: max-height 0.3s ease-out;
}

.report-container .section-content.collapsed {
    max-height: 0;
    overflow: hidden;
}

/* ===== 段落与列表 ===== */
.report-container p {
    margin: 12px 0;
    text-align: justify;
}

.report-container ul, .report-container ol {
    padding-left: 24px;
    margin: 10px 0;
}

.report-container li {
    margin: 6px 0;
    padding-left: 8px;
}

.report-container ul li::marker {
    color: #4299e1;
}

.report-container ol li::marker {
    color: #4299e1;
    font-weight: 500;
}

/* ===== 嵌套列表层级缩进 ===== */
.report-container ul ul, .report-container ol ol,
.report-container ul ol, .report-container ol ul {
    margin: 4px 0;
    padding-left: 20px;
}

.report-container ul ul li::marker,
.report-container ol ol li::marker {
    color: #718096;
    font-size: 0.9em;
}

/* ===== 表格样式 ===== */
.report-container table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 0.95em;
}

.report-container th {
    background: linear-gradient(135deg, #3182ce 0%, #2c5282 100%);
    color: white;
    font-weight: 600;
    padding: 12px 10px;
    text-align: left;
    border: 1px solid #2c5282;
}

.report-container td {
    padding: 10px;
    border: 1px solid #e2e8f0;
    vertical-align: top;
}

.report-container tr:nth-child(even) {
    background-color: #f7fafc;
}

.report-container tr:hover {
    background-color: #edf2f7;
}

/* ===== 指标颜色编码 ===== */
/* 正向指标（通过、良好、显著）- 绿色 */
.metric-positive {
    color: #276749;
    font-weight: 500;
}

.metric-positive .metric-value {
    color: #38a169;
    font-weight: 600;
}

/* 负向指标（未通过、差、冲突）- 红色 */
.metric-negative {
    color: #c53030;
    font-weight: 500;
}

.metric-negative .metric-value {
    color: #e53e3e;
    font-weight: 600;
}

/* 中性指标 - 蓝色 */
.metric-neutral {
    color: #2b6cb0;
}

.metric-neutral .metric-value {
    color: #3182ce;
}

/* 警告/缺失产物 - 黄色 */
.metric-warning {
    color: #744210;
    background-color: #fefcbf;
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: 500;
}

/* 冲突/错误 - 红色加粗 */
.metric-error {
    color: #c53030;
    background-color: #fed7d7;
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: 700;
}

/* 高亮重要结论 */
.conclusion-highlight {
    color: #2c5282;
    font-weight: 600;
    background: linear-gradient(120deg, #ebf8ff 0%, #bee3f8 100%);
    padding: 4px 8px;
    border-radius: 4px;
    border-left: 4px solid #3182ce;
}

/* ===== 代码块 ===== */
.report-container code {
    background: #f1f5f9;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'SF Mono', Consolas, 'Liberation Mono', monospace;
    font-size: 0.9em;
    color: #3182ce;
}

.report-container pre {
    background: #1a202c;
    color: #e2e8f0;
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 16px 0;
}

.report-container pre code {
    background: transparent;
    color: inherit;
    padding: 0;
}

/* ===== 分割线和间距 ===== */
.report-container hr {
    border: none;
    border-top: 2px solid #e2e8f0;
    margin: 24px 0;
}

.report-container .section-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #cbd5e0, transparent);
    margin: 32px 0;
}

/* ===== 摘要/摘要框 ===== */
.abstract-box {
    background: linear-gradient(135deg, #ebf8ff 0%, #e6fffa 100%);
    border: 1px solid #90cdf4;
    border-left: 5px solid #3182ce;
    border-radius: 8px;
    padding: 20px 24px;
    margin: 20px 0;
}

.abstract-box h2 {
    color: #2c5282;
    border-bottom: none;
    margin-top: 0;
}

/* ===== 统计卡片 ===== */
.stat-card {
    display: inline-block;
    background: #f7fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px 20px;
    margin: 8px;
    min-width: 120px;
    text-align: center;
}

.stat-card .stat-label {
    font-size: 0.85em;
    color: #718096;
    margin-bottom: 4px;
}

.stat-card .stat-value {
    font-size: 1.5em;
    font-weight: 700;
    color: #2d3748;
}

.stat-card .stat-value.positive {
    color: #38a169;
}

.stat-card .stat-value.negative {
    color: #e53e3e;
}

/* ===== 标签式标记 ===== */
.tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.85em;
    font-weight: 500;
}

.tag-pass {
    background: #c6f6d5;
    color: #276749;
}

.tag-fail {
    background: #fed7d7;
    color: #c53030;
}

.tag-warn {
    background: #fefcbf;
    color: #744210;
}

.tag-info {
    background: #bee3f8;
    color: #2b6cb0;
}
"""

REPORT_JAVASCRIPT = """
document.addEventListener('DOMContentLoaded', function() {
    // 折叠功能：使用 details/summary 原生HTML折叠元素
    const container = document.querySelector('.report-container');
    if (!container) return;

    // 找到所有h2, h3, h4标题
    const headings = container.querySelectorAll('h2, h3, h4');

    // 要默认折叠的小节标题关键词
    const defaultCollapsedKeywords = [
        '一致性与冲突',
        '计划产物',
        '执行事实',
        '证据摘录',
        '判定依据',
        '恢复计划',
        '校准',
        '路径对照',
    ];

    headings.forEach(function(heading) {
        // 检查是否应该默认折叠
        const headingText = heading.textContent || '';
        const shouldCollapse = defaultCollapsedKeywords.some(function(kw) {
            return headingText.includes(kw);
        });

        // 创建details元素
        const details = document.createElement('details');
        details.className = 'collapsible-section';

        if (shouldCollapse) {
            details.open = false;  // 默认折叠
        } else {
            details.open = true;  // 默认展开
        }

        // 创建summary
        const summary = document.createElement('summary');
        summary.innerHTML = heading.innerHTML;
        summary.style.cursor = 'pointer';
        summary.style.listStyle = 'none';
        summary.style.display = 'flex';
        summary.style.alignItems = 'center';
        summary.style.gap = '8px';

        // 如果已有collapse-arrow则不重复添加
        const existingArrow = summary.querySelector('.collapse-arrow');
        if (!existingArrow) {
            const arrow = document.createElement('span');
            arrow.className = 'collapse-arrow';
            arrow.textContent = shouldCollapse ? '▶' : '▼';
            arrow.style.fontSize = '0.7em';
            arrow.style.color = '#718096';
            arrow.style.transition = 'transform 0.2s';
            summary.insertBefore(arrow, summary.firstChild);
        }

        // 点击时切换箭头方向
        summary.addEventListener('click', function(e) {
            e.preventDefault();
            details.open = !details.open;
            const arrow = summary.querySelector('.collapse-arrow');
            if (arrow) {
                arrow.textContent = details.open ? '▼' : '▶';
            }
        });

        // 替换原标题
        heading.parentNode.insertBefore(details, heading);
        details.appendChild(summary);

        // 将标题后的内容移入details（直到下一个同级标题）
        const parent = heading.parentNode;
        let next = heading.nextElementSibling;
        while (next) {
            if (next.tagName === 'H2' || next.tagName === 'H3' || next.tagName === 'H4' || next.tagName === 'H5') {
                break;
            }
            const toMove = next;
            next = next.nextElementSibling;
            details.appendChild(toMove);
        }
        // 移除原标题
        heading.remove();
    });

    // 添加CSS样式
    const style = document.createElement('style');
    style.textContent = `
        .collapsible-section {
            margin: 12px 0;
        }
        .collapsible-section summary {
            user-select: none;
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
        }
        .collapsible-section summary::-webkit-details-marker {
            display: none;
        }
        .collapsible-section summary:hover {
            background-color: #f1f5f9;
        }
/* 标题层级样式 - 用于span.heading-level-N */
.heading-level-1 {
    font-size: 1.4em;
    font-weight: 700;
    color: #1e40af;
    border-bottom: 3px solid #3b82f6;
    padding-bottom: 8px;
    margin-bottom: 8px;
    margin-top: 16px;
    display: block;
}
.heading-level-2 {
    font-size: 1.2em;
    font-weight: 600;
    color: #1e293b;
    border-left: 4px solid #3b82f6;
    padding-left: 12px;
    margin: 8px 0;
    display: block;
}
.heading-level-3 {
    font-size: 1.1em;
    font-weight: 600;
    color: #475569;
    padding-left: 16px;
    margin: 6px 0;
    display: block;
}
.heading-level-4 {
    font-size: 1em;
    font-weight: 600;
    color: #334155;
    padding: 4px 0;
    margin: 4px 0;
    display: block;
}
/* 段落间距控制 */
.report-container p {
    margin: 3px 0;
    line-height: 1.5;
}
/* 列表项间距缩小 */
.report-container li {
    margin: 2px 0;
    line-height: 1.4;
}
/* 减少连续段落之间的空行 */
.report-container p + p {
    margin-top: 2px;
}
/* 标题下方内容紧贴标题 */
.report-container .heading-level-1 + *,
.report-container .heading-level-2 + *,
.report-container .heading-level-3 + *,
.report-container .heading-level-4 + * {
    margin-top: 4px;
}
details.collapsible-section > *:not(summary) {
    margin-left: 24px;
    padding: 3px 0;
}
details.collapsible-section > summary {
    padding: 6px 8px;
}
.collapse-arrow {
    font-size: 0.7em;
    color: #64748b;
    transition: transform 0.2s;
}
    `;
    document.head.appendChild(style);
});
"""

def get_report_styles() -> tuple[str, str]:
    """返回 (CSS样式, JavaScript)"""
    return REPORT_CSS, REPORT_JAVASCRIPT


def wrap_html_with_styles(html_body: str, title: str = "分析报告") -> str:
    """将HTML内容包裹在完整文档中，包含样式和交互"""
    css, js = get_report_styles()
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{css}
    </style>
</head>
<body>
    <div class="report-container">
{html_body}
    </div>
    <script>
{js}
    </script>
</body>
</html>"""
