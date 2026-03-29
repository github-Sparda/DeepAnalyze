"""
Statistics Runner - 统一统计分析入口

提供一致的统计分析流程，统一调用方式，标准化输出。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd


class StatisticsRunner:
    """
    统一统计分析入口类

    提供:
    - 描述性统计
    - 推断统计 (t检验)
    - 多重比较校正 (FDR/Bonferroni)
    - 效应量 (Cohen's d)
    - 统计结果标准化输出
    """

    def __init__(self):
        self.results: dict[str, Any] = {}

    def run_descriptive(
        self,
        data: pd.DataFrame,
        columns: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        描述性统计

        Args:
            data: 输入数据
            columns: 要分析的列名，None表示所有数值列

        Returns:
            描述性统计结果
        """
        if columns is None:
            columns = data.select_dtypes(include=[np.number]).columns.tolist()

        desc_results = {}
        for col in columns:
            if col in data.columns:
                values = data[col].dropna()
                desc_results[col] = {
                    "n": int(len(values)),
                    "mean": float(values.mean()) if len(values) > 0 else None,
                    "std": float(values.std()) if len(values) > 0 else None,
                    "min": float(values.min()) if len(values) > 0 else None,
                    "max": float(values.max()) if len(values) > 0 else None,
                    "median": float(values.median()) if len(values) > 0 else None,
                    "q25": float(values.quantile(0.25)) if len(values) > 0 else None,
                    "q75": float(values.quantile(0.75)) if len(values) > 0 else None,
                    "missing": int(data[col].isna().sum()),
                }

        self.results["descriptive"] = desc_results
        return desc_results

    def run_ttest(
        self,
        group_a: np.ndarray,
        group_b: np.ndarray,
        labels: tuple[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        独立样本t检验

        Args:
            group_a: A组数据
            group_b: B组数据
            labels: (A组标签, B组标签)

        Returns:
            t检验结果
        """
        import math

        def _normal_p_value(z: float) -> float:
            return 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))

        if group_a.size == 0 or group_b.size == 0:
            return {"status": "error", "message": "Empty group"}

        mean_a = float(np.mean(group_a))
        mean_b = float(np.mean(group_b))
        mean_diff = mean_a - mean_b

        var_a = np.var(group_a, ddof=1) if group_a.size > 1 else 0.0
        var_b = np.var(group_b, ddof=1) if group_b.size > 1 else 0.0

        se = math.sqrt(var_a / max(group_a.size, 1) + var_b / max(group_b.size, 1))
        if se == 0:
            p_val = 1.0
            t_stat = 0.0
        else:
            t_stat = mean_diff / se
            p_val = _normal_p_value(t_stat)

        pooled = math.sqrt(
            ((group_a.size - 1) * var_a + (group_b.size - 1) * var_b)
            / max(group_a.size + group_b.size - 2, 1)
        )
        cohens_d = mean_diff / pooled if pooled else 0.0

        eps = 1e-9
        fold_change = (mean_b + eps) / (mean_a + eps)

        ci_low = mean_diff - 1.96 * se
        ci_high = mean_diff + 1.96 * se

        result = {
            "test": "t_test",
            "group_a": labels[0] if labels else "A",
            "group_b": labels[1] if labels else "B",
            "n_a": int(group_a.size),
            "n_b": int(group_b.size),
            "mean_a": mean_a,
            "mean_b": mean_b,
            "mean_diff": mean_diff,
            "fold_change": fold_change,
            "log2_fold_change": math.log2(fold_change) if fold_change > 0 else 0.0,
            "p_value": p_val,
            "t_stat": t_stat,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "cohens_d": cohens_d,
            "effect_size_interpretation": self._interpret_cohens_d(cohens_d),
        }

        self.results["ttest"] = result
        return result

    def run_multiple_testing_correction(
        self,
        p_values: list[float],
        method: Literal["fdr_bh", "bonferroni"] = "fdr_bh",
    ) -> dict[str, Any]:
        """
        多重比较校正

        Args:
            p_values: 原始p值列表
            method: 'fdr_bh' (Benjamini-Hochberg) 或 'bonferroni'

        Returns:
            校正后的结果
        """
        pvals = np.array(p_values)
        n = len(pvals)

        if n == 0:
            return {"status": "error", "message": "No p-values"}

        if method == "bonferroni":
            q_values = np.clip(pvals * n, 0, 1)
        elif method == "fdr_bh":
            sorted_idx = np.argsort(pvals)
            sorted_p = pvals[sorted_idx]
            q_values = np.empty(n, dtype=float)
            prev = 1.0
            for i in range(n - 1, -1, -1):
                rank = i + 1
                val = sorted_p[i] * n / rank
                prev = min(prev, val)
                q_values[i] = prev
            inv_idx = np.argsort(sorted_idx)
            q_values = q_values[inv_idx]
        else:
            q_values = pvals

        result = {
            "method": method,
            "n_tests": int(n),
            "p_values": pvals.tolist(),
            "q_values": q_values.tolist(),
            "significant_q005": int(np.sum(q_values < 0.05)),
            "significant_q001": int(np.sum(q_values < 0.01)),
            "alpha": 0.05,
        }

        self.results["multiple_testing"] = result
        return result

    def run_correlation(
        self,
        data: pd.DataFrame,
        method: Literal["pearson", "spearman"] = "pearson",
    ) -> dict[str, Any]:
        """
        相关性分析

        Args:
            data: 输入数据
            method: 'pearson' 或 'spearman'

        Returns:
            相关性矩阵
        """
        numeric_data = data.select_dtypes(include=[np.number])
        if numeric_data.shape[1] < 2:
            return {"status": "skipped", "message": "Need at least 2 numeric columns"}

        if method == "pearson":
            corr_matrix = numeric_data.corr(method="pearson")
        else:
            corr_matrix = numeric_data.corr(method="spearman")

        result = {
            "method": method,
            "n_features": int(numeric_data.shape[1]),
            "correlation_matrix": corr_matrix.to_dict(),
        }

        self.results["correlation"] = result
        return result

    def run_full_analysis(
        self,
        df: pd.DataFrame,
        group_col: str | None = None,
        numeric_cols: list[str] | None = None,
        multiple_testing_method: Literal["fdr_bh", "bonferroni"] = "fdr_bh",
    ) -> dict[str, Any]:
        """
        运行完整统计分析流程

        流程:
        1. 描述性统计
        2. 组间t检验
        3. 多重比较校正
        4. 效应量计算

        Args:
            df: 输入数据
            group_col: 分组列名
            numeric_cols: 数值列名列表
            multiple_testing_method: 多重比较校正方法

        Returns:
            完整统计分析结果
        """
        self.results = {"status": "ok"}

        if numeric_cols is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.run_descriptive(df, numeric_cols)

        if group_col and len(df[group_col].unique()) >= 2:
            groups = df[group_col].dropna().unique().tolist()
            if len(groups) >= 2:
                g1, g2 = groups[:2]
                df1 = df[df[group_col] == g1]
                df2 = df[df[group_col] == g2]

                ttest_results = []
                p_values = []

                for col in numeric_cols:
                    if col in df.columns:
                        a = df1[col].dropna().values
                        b = df2[col].dropna().values
                        if len(a) > 0 and len(b) > 0:
                            tt_result = self.run_ttest(a, b, labels=(str(g1), str(g2)))
                            tt_result["feature"] = col
                            ttest_results.append(tt_result)
                            p_values.append(tt_result["p_value"])

                self.results["ttest_per_feature"] = ttest_results

                if p_values:
                    self.run_multiple_testing_correction(p_values, method=multiple_testing_method)
        else:
            self.run_correlation(df)

        return self.results

    def get_summary(self) -> dict[str, Any]:
        """
        获取统计结果摘要

        Returns:
            结果摘要
        """
        summary = {"status": self.results.get("status", "unknown")}

        if "ttest_per_feature" in self.results:
            features = self.results["ttest_per_feature"]
            p_vals = [f["p_value"] for f in features]
            summary["n_features"] = len(features)
            summary["n_significant_p005"] = len([p for p in p_vals if p < 0.05])
            summary["n_significant_q005"] = 0
            if "multiple_testing" in self.results:
                q_vals = self.results["multiple_testing"]["q_values"]
                summary["n_significant_q005"] = len([q for q in q_vals if q < 0.05])

        return summary

    @staticmethod
    def _interpret_cohens_d(d: float) -> str:
        """解释Cohen's d效应量大小"""
        abs_d = abs(d)
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"

    @staticmethod
    def get_output_schema() -> dict[str, Any]:
        """
        获取输出JSON schema

        Returns:
            标准化的输出格式说明
        """
        return {
            "descriptive": {
                "type": "object",
                "description": "各特征的描述性统计",
                "properties": {
                    "n": "样本数",
                    "mean": "均值",
                    "std": "标准差",
                    "min": "最小值",
                    "max": "最大值",
                    "median": "中位数",
                    "q25": "25%分位数",
                    "q75": "75%分位数",
                    "missing": "缺失值数量",
                },
            },
            "ttest": {
                "type": "object",
                "description": "t检验结果",
                "properties": {
                    "p_value": "原始p值",
                    "q_value": "校正后q值",
                    "cohens_d": "效应量(Cohen's d)",
                    "effect_size_interpretation": "效应量解释",
                    "fold_change": "fold change",
                    "log2_fold_change": "log2 fold change",
                },
            },
            "multiple_testing": {
                "type": "object",
                "description": "多重比较校正结果",
                "properties": {
                    "method": "校正方法",
                    "n_tests": "检验次数",
                    "q_values": "校正后q值列表",
                    "significant_q005": "q<0.05的显著特征数",
                },
            },
        }
