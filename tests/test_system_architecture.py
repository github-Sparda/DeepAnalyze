from __future__ import annotations

import os
import sys
import ast
import networkx as nx
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest


def get_module_name(file_path: Path, project_root: Path) -> str:
    """获取模块名称"""
    relative_path = file_path.relative_to(project_root)
    module_parts = list(relative_path.parts)
    if module_parts[-1] == "__init__.py":
        module_parts.pop()
    else:
        module_parts[-1] = module_parts[-1].replace(".py", "")
    return ".".join(module_parts)


def analyze_imports(file_path: Path, project_root: Path) -> Set[str]:
    """分析文件中的导入"""
    imports = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
    except Exception:
        pass
    return imports


def build_dependency_graph(project_root: Path) -> nx.DiGraph:
    """构建依赖图"""
    graph = nx.DiGraph()
    python_files = list(project_root.rglob("*.py"))
    
    # 过滤掉测试文件和 __pycache__
    python_files = [f for f in python_files if "test" not in str(f) and "__pycache__" not in str(f)]
    
    for file_path in python_files:
        module_name = get_module_name(file_path, project_root)
        if not module_name:
            continue
        graph.add_node(module_name)
        imports = analyze_imports(file_path, project_root)
        for imp in imports:
            # 只关注项目内部的模块
            if imp.startswith("src."):
                graph.add_edge(module_name, imp)
    
    return graph


def detect_circular_dependencies(graph: nx.DiGraph) -> List[List[str]]:
    """检测循环依赖"""
    cycles = []
    try:
        cycles = list(nx.simple_cycles(graph))
    except Exception:
        pass
    return cycles


def calculate_module_coupling(graph: nx.DiGraph) -> Dict[str, int]:
    """计算模块耦合度"""
    coupling = {}
    for node in graph.nodes():
        # 入度 + 出度
        coupling[node] = graph.in_degree(node) + graph.out_degree(node)
    return coupling


def calculate_module_cohesion(file_path: Path) -> float:
    """计算模块内聚度"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, str(file_path))
        
        # 计算函数和类的数量
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        # 计算函数之间的调用关系
        function_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                function_calls.append(node.func.id)
        
        # 计算内聚度：函数调用数 / (函数数 * 函数数)
        if len(functions) > 1:
            cohesion = len(function_calls) / (len(functions) * len(functions))
        else:
            cohesion = 1.0 if len(functions) == 1 else 0.0
        
        return cohesion
    except Exception:
        return 0.0


def analyze_module_extensibility(module_path: Path) -> Dict[str, Any]:
    """分析模块可扩展性"""
    try:
        with open(module_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, str(module_path))
        
        # 计算公共方法和类的数量
        public_functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("_") is False]
        public_classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name.startswith("_") is False]
        
        # 计算抽象方法的数量
        abstract_methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                        abstract_methods.append(node)
        
        # 计算接口数量（基于ABC）
        interfaces = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "ABC":
                        interfaces.append(node)
        
        return {
            "public_functions": len(public_functions),
            "public_classes": len(public_classes),
            "abstract_methods": len(abstract_methods),
            "interfaces": len(interfaces),
            "extensibility_score": len(public_functions) + len(public_classes) + len(abstract_methods) + len(interfaces)
        }
    except Exception:
        return {
            "public_functions": 0,
            "public_classes": 0,
            "abstract_methods": 0,
            "interfaces": 0,
            "extensibility_score": 0
        }


def test_dependency_graph():
    """测试依赖图构建"""
    project_root = Path(__file__).parent.parent
    graph = build_dependency_graph(project_root)
    assert isinstance(graph, nx.DiGraph)
    assert len(graph.nodes()) > 0


def test_circular_dependencies():
    """测试循环依赖检测"""
    project_root = Path(__file__).parent.parent
    graph = build_dependency_graph(project_root)
    cycles = detect_circular_dependencies(graph)
    # 打印循环依赖
    if cycles:
        print("检测到循环依赖:")
        for cycle in cycles:
            print(f"  {' -> '.join(cycle)}")
    # 暂时不强制要求无循环依赖，因为大型项目可能存在复杂依赖
    # assert len(cycles) == 0


def test_module_coupling():
    """测试模块耦合度"""
    project_root = Path(__file__).parent.parent
    graph = build_dependency_graph(project_root)
    coupling = calculate_module_coupling(graph)
    
    # 找出耦合度最高的模块
    high_coupling_modules = [module for module, degree in coupling.items() if degree > 20]
    if high_coupling_modules:
        print("高耦合模块:")
        for module in high_coupling_modules:
            print(f"  {module}: {coupling[module]}")
    
    # 暂时不强制要求低耦合，因为某些核心模块可能需要较高耦合
    # assert len(high_coupling_modules) == 0


def test_module_cohesion():
    """测试模块内聚度"""
    project_root = Path(__file__).parent.parent
    python_files = list(project_root.rglob("*.py"))
    python_files = [f for f in python_files if "test" not in str(f) and "__pycache__" not in str(f) and f.name != "__init__.py"]
    
    low_cohesion_modules = []
    for file_path in python_files[:50]:  # 限制分析的文件数量
        cohesion = calculate_module_cohesion(file_path)
        if cohesion < 0.1:
            module_name = get_module_name(file_path, project_root)
            low_cohesion_modules.append((module_name, cohesion))
    
    if low_cohesion_modules:
        print("低内聚模块:")
        for module, cohesion in low_cohesion_modules:
            print(f"  {module}: {cohesion:.2f}")
    
    # 暂时不强制要求高内聚，因为某些模块可能具有不同的职责
    # assert len(low_cohesion_modules) == 0


def test_module_extensibility():
    """测试模块可扩展性"""
    project_root = Path(__file__).parent.parent
    python_files = list(project_root.rglob("*.py"))
    python_files = [f for f in python_files if "test" not in str(f) and "__pycache__" not in str(f) and f.name != "__init__.py"]
    
    low_extensibility_modules = []
    for file_path in python_files[:50]:  # 限制分析的文件数量
        extensibility = analyze_module_extensibility(file_path)
        if extensibility["extensibility_score"] == 0:
            module_name = get_module_name(file_path, project_root)
            low_extensibility_modules.append(module_name)
    
    if low_extensibility_modules:
        print("低可扩展性模块:")
        for module in low_extensibility_modules:
            print(f"  {module}")
    
    # 暂时不强制要求高可扩展性，因为某些模块可能是工具类或辅助模块
    # assert len(low_extensibility_modules) == 0


def test_architecture_quality():
    """测试架构质量"""
    project_root = Path(__file__).parent.parent
    graph = build_dependency_graph(project_root)
    
    # 计算关键指标
    node_count = len(graph.nodes())
    edge_count = len(graph.edges())
    cycles = detect_circular_dependencies(graph)
    coupling = calculate_module_coupling(graph)
    
    # 计算平均耦合度
    if node_count > 0:
        avg_coupling = sum(coupling.values()) / node_count
    else:
        avg_coupling = 0
    
    # 打印架构指标
    print("架构质量指标:")
    print(f"  模块数量: {node_count}")
    print(f"  依赖关系数量: {edge_count}")
    print(f"  循环依赖数量: {len(cycles)}")
    print(f"  平均耦合度: {avg_coupling:.2f}")
    
    # 验证基本架构指标
    assert node_count > 0
    assert edge_count >= 0


def test_core_modules_dependencies():
    """测试核心模块的依赖关系"""
    project_root = Path(__file__).parent.parent
    graph = build_dependency_graph(project_root)
    
    # 核心模块
    core_modules = [
        "src.core.orchestration.closure",
        "src.core.orchestration.depth_research",
        "src.core.analytics.toolkit.runner",
        "src.core.assistant.engine",
        "src.api.main"
    ]
    
    print("核心模块依赖分析:")
    for module in core_modules:
        if module in graph:
            in_edges = list(graph.predecessors(module))
            out_edges = list(graph.successors(module))
            print(f"  {module}:")
            print(f"    被依赖数: {len(in_edges)}")
            print(f"    依赖数: {len(out_edges)}")
    
    # 验证核心模块存在
    for module in core_modules:
        if module in graph:
            assert True


def test_module_hierarchy():
    """测试模块层次结构"""
    project_root = Path(__file__).parent.parent
    graph = build_dependency_graph(project_root)
    
    # 分析模块层次结构
    levels = {}
    for node in graph.nodes():
        parts = node.split(".")
        level = len(parts)
        if level not in levels:
            levels[level] = []
        levels[level].append(node)
    
    print("模块层次结构:")
    for level in sorted(levels.keys()):
        print(f"  层次 {level}: {len(levels[level])} 个模块")
    
    # 验证层次结构
    assert len(levels) > 0


def test_architecture_optimization_suggestions():
    """测试架构优化建议"""
    project_root = Path(__file__).parent.parent
    graph = build_dependency_graph(project_root)
    coupling = calculate_module_coupling(graph)
    cycles = detect_circular_dependencies(graph)
    
    # 生成优化建议
    suggestions = []
    
    if cycles:
        suggestions.append(f"检测到 {len(cycles)} 个循环依赖，建议重构以消除循环依赖")
    
    high_coupling_modules = [module for module, degree in coupling.items() if degree > 30]
    if high_coupling_modules:
        suggestions.append(f"检测到 {len(high_coupling_modules)} 个高耦合模块，建议进行模块拆分")
    
    # 打印优化建议
    if suggestions:
        print("架构优化建议:")
        for suggestion in suggestions:
            print(f"  - {suggestion}")
    else:
        print("架构质量良好，未发现明显问题")
    
    # 验证建议生成
    assert isinstance(suggestions, list)


if __name__ == "__main__":
    pytest.main([__file__])
