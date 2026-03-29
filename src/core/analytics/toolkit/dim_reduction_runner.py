"""
Dimension Reduction Runner - 降维算法统一入口

提供多种降维算法的统一调用方式。
"""

from __future__ import annotations

from typing import Any, Literal, Optional

import numpy as np
import pandas as pd


class DimReductionRunner:
    """
    降维算法统一入口

    支持算法:
    - pca: 主成分分析
    - lda: 线性判别分析
    - ica: 独立成分分析
    - factor: 因子分析
    - truncated_svd: 截断SVD
    """

    SUPPORTED_METHODS = ["pca", "lda", "ica", "factor", "truncated_svd"]

    def __init__(self):
        self.results: dict[str, Any] = {}
        self.model: Any = None
        self.components_: Optional[np.ndarray] = None
        self.transformed_data_: Optional[np.ndarray] = None

    def run(
        self,
        data: pd.DataFrame | np.ndarray,
        method: Literal["pca", "lda", "ica", "factor", "truncated_svd", "auto"] = "auto",
        n_components: int | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        运行降维分析

        Args:
            data: 输入数据
            method: 降维算法
            n_components: 目标维度数
            **kwargs: 其他参数

        Returns:
            降维结果
        """
        if isinstance(data, pd.DataFrame):
            X = data.select_dtypes(include=[np.number]).values
            feature_names = data.select_dtypes(include=[np.number]).columns.tolist()
        else:
            X = data
            feature_names = [f"feat_{i}" for i in range(X.shape[1])]

        if n_components is None:
            n_components = min(10, X.shape[1], X.shape[0])

        if method == "auto":
            method = "pca"

        if method == "pca":
            return self._run_pca(X, n_components, feature_names, **kwargs)
        elif method == "lda":
            return self._run_lda(X, n_components, feature_names, **kwargs)
        elif method == "ica":
            return self._run_ica(X, n_components, feature_names, **kwargs)
        elif method == "factor":
            return self._run_factor(X, n_components, feature_names, **kwargs)
        elif method == "truncated_svd":
            return self._run_truncated_svd(X, n_components, feature_names, **kwargs)
        else:
            return {"status": "error", "message": f"Unknown method: {method}"}

    def _run_pca(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        self.model = PCA(n_components=n_components, **kwargs)
        self.components_ = self.model.fit_transform(X_scaled)
        self.transformed_data_ = self.components_

        explained_var = self.model.explained_variance_ratio_
        cumsum_var = np.cumsum(explained_var)

        components_df = pd.DataFrame(
            self.model.components_,
            columns=feature_names,
            index=[f"PC{i+1}" for i in range(n_components)]
        )

        self.results = {
            "method": "pca",
            "n_components": n_components,
            "transformed_data": self.components_[:, :5].tolist(),
            "explained_variance_ratio": explained_var.tolist(),
            "cumulative_variance_ratio": cumsum_var.tolist(),
            "components": components_df.to_dict(orient="index"),
            "metrics": {
                "total_variance_explained": round(float(cumsum_var[-1]), 4) if len(cumsum_var) > 0 else 0,
                "n_components_95": int(np.argmax(cumsum_var >= 0.95) + 1) if any(cumsum_var >= 0.95) else n_components,
            },
        }
        return self.results

    def _run_lda(
        self, X: np.ndarray, n_components: int, feature_names: list[str], y: Optional[np.ndarray] = None, **kwargs
    ) -> dict[str, Any]:
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

        if y is None:
            return {"status": "error", "message": "LDA requires y (labels)"}

        n_classes = len(np.unique(y))
        max_components = min(n_components, n_classes - 1)

        if max_components < 1:
            return {"status": "error", "message": "Not enough classes for LDA"}

        self.model = LinearDiscriminantAnalysis(n_components=max_components, **kwargs)
        self.components_ = self.model.fit_transform(X, y)
        self.transformed_data_ = self.components_

        explained_var = self.model.explained_variance_ratio_ if hasattr(self.model, "explained_variance_ratio_") else None

        components_df = pd.DataFrame(
            self.model.scalings_[:, :max_components] if hasattr(self.model, "scalings_") else self.model.components_[:, :max_components],
            columns=[f"LD{i+1}" for i in range(max_components)],
            index=feature_names,
        )

        self.results = {
            "method": "lda",
            "n_components": max_components,
            "n_classes": n_classes,
            "transformed_data": self.components_[:, :5].tolist() if self.components_ is not None else None,
            "explained_variance_ratio": explained_var.tolist() if explained_var is not None else None,
            "scalings": components_df.to_dict(orient="index") if hasattr(self.model, "scalings_") else None,
            "metrics": {
                "n_components": max_components,
                "n_classes": n_classes,
            },
        }
        return self.results

    def _run_ica(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.decomposition import FastICA
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        self.model = FastICA(n_components=n_components, random_state=42, max_iter=1000, **kwargs)
        self.components_ = self.model.fit_transform(X_scaled)
        self.transformed_data_ = self.components_

        kurtosis = self._compute_kurtosis(self.components_)

        mixing_df = pd.DataFrame(
            self.model.mixing_,
            columns=[f"IC{i+1}" for i in range(n_components)],
            index=feature_names,
        )

        self.results = {
            "method": "ica",
            "n_components": n_components,
            "transformed_data": self.components_[:, :5].tolist(),
            "mixing_matrix": mixing_df.to_dict(orient="index"),
            "kurtosis": kurtosis.tolist(),
            "metrics": {
                "mean_kurtosis": round(float(np.mean(kurtosis)), 4),
            },
        }
        return self.results

    def _run_factor(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.decomposition import FactorAnalysis
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        self.model = FactorAnalysis(n_components=n_components, random_state=42, **kwargs)
        self.components_ = self.model.fit_transform(X_scaled)
        self.transformed_data_ = self.components_

        components_df = pd.DataFrame(
            self.model.components_,
            columns=[f"Factor{i+1}" for i in range(n_components)],
            index=feature_names,
        )

        self.results = {
            "method": "factor",
            "n_components": n_components,
            "transformed_data": self.components_[:, :5].tolist(),
            "components": components_df.to_dict(orient="index"),
            "noise_variance": self.model.noise_variance_.tolist() if hasattr(self.model, "noise_variance_") else None,
            "metrics": {
                "n_components": n_components,
            },
        }
        return self.results

    def _run_truncated_svd(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.decomposition import TruncatedSVD

        self.model = TruncatedSVD(n_components=n_components, random_state=42, **kwargs)
        self.components_ = self.model.fit_transform(X)
        self.transformed_data_ = self.components_

        explained_var = self.model.explained_variance_ratio_
        cumsum_var = np.cumsum(explained_var)

        self.results = {
            "method": "truncated_svd",
            "n_components": n_components,
            "transformed_data": self.components_[:, :5].tolist(),
            "explained_variance_ratio": explained_var.tolist(),
            "cumulative_variance_ratio": cumsum_var.tolist(),
            "singular_values": self.model.singular_values_.tolist() if hasattr(self.model, "singular_values_") else None,
            "metrics": {
                "total_variance_explained": round(float(cumsum_var[-1]), 4) if len(cumsum_var) > 0 else 0,
            },
        }
        return self.results

    @staticmethod
    def _compute_kurtosis(X: np.ndarray) -> np.ndarray:
        """计算峰度"""
        from scipy.stats import kurtosis
        return kurtosis(X, axis=0)

    def get_component_loadings(self) -> pd.DataFrame | None:
        """获取成分载荷矩阵"""
        if self.results.get("method") == "pca" and "components" in self.results:
            return pd.DataFrame.from_dict(self.results["components"])
        return None

    def get_summary(self) -> dict[str, Any]:
        """获取结果摘要"""
        if not self.results:
            return {"status": "error", "message": "Run dimension reduction first"}

        summary = {
            "method": self.results.get("method"),
            "n_components": self.results.get("n_components"),
        }

        if "metrics" in self.results:
            summary["metrics"] = self.results["metrics"]

        return summary
