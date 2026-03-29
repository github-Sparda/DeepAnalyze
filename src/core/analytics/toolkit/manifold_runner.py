"""
Manifold Runner - 流形学习统一入口

提供多种流形学习算法的统一调用方式。
"""

from __future__ import annotations

from typing import Any, Literal, Optional

import numpy as np
import pandas as pd


class ManifoldRunner:
    """
    流形学习统一入口

    支持算法:
    - isomap: Isomap等距映射
    - lle: 局部线性嵌入
    - mds: 多维缩放
    - tsne: t-SNE
    - spectral_embedding: 谱嵌入
    - locally_linear_embedding: 局部线性嵌入
    """

    SUPPORTED_METHODS = ["isomap", "lle", "mds", "tsne", "spectral_embedding", "locally_linear_embedding"]

    def __init__(self):
        self.results: dict[str, Any] = {}
        self.model: Any = None
        self.embedding_: Optional[np.ndarray] = None

    def run(
        self,
        data: pd.DataFrame | np.ndarray,
        method: Literal["isomap", "lle", "mds", "tsne", "spectral_embedding", "locally_linear_embedding", "auto"] = "auto",
        n_components: int = 2,
        **kwargs,
    ) -> dict[str, Any]:
        """
        运行流形学习分析

        Args:
            data: 输入数据
            method: 流形学习算法
            n_components: 目标维度数
            **kwargs: 其他参数

        Returns:
            流形学习结果
        """
        if isinstance(data, pd.DataFrame):
            X = data.select_dtypes(include=[np.number]).values
            feature_names = data.select_dtypes(include=[np.number]).columns.tolist()
        else:
            X = data
            feature_names = [f"feat_{i}" for i in range(X.shape[1])]

        if method == "auto":
            n_samples = X.shape[0]
            if n_samples > 5000:
                method = "spectral_embedding"
            elif n_samples > 2000:
                method = "mds"
            else:
                method = "lle"

        if method == "isomap":
            return self._run_isomap(X, n_components, feature_names, **kwargs)
        elif method == "lle":
            return self._run_lle(X, n_components, feature_names, **kwargs)
        elif method == "mds":
            return self._run_mds(X, n_components, feature_names, **kwargs)
        elif method == "tsne":
            return self._run_tsne(X, n_components, feature_names, **kwargs)
        elif method == "spectral_embedding":
            return self._run_spectral_embedding(X, n_components, feature_names, **kwargs)
        elif method == "locally_linear_embedding":
            return self._run_locally_linear_embedding(X, n_components, feature_names, **kwargs)
        else:
            return {"status": "error", "message": f"Unknown method: {method}"}

    def _run_isomap(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.manifold import Isomap
        from sklearn.preprocessing import StandardScaler

        n_neighbors = kwargs.pop("n_neighbors", min(30, X.shape[0] - 1))

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        self.model = Isomap(n_neighbors=n_neighbors, n_components=n_components, **kwargs)
        self.embedding_ = self.model.fit_transform(X_scaled)

        reconstruction_error = self.model.reconstruction_error()

        self.results = {
            "method": "isomap",
            "n_components": n_components,
            "embedding": self.embedding_[:, :5].tolist(),
            "n_neighbors": n_neighbors,
            "metrics": {
                "reconstruction_error": round(reconstruction_error, 6),
            },
        }
        return self.results

    def _run_lle(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.manifold import LocallyLinearEmbedding
        from sklearn.preprocessing import StandardScaler

        n_neighbors = kwargs.pop("n_neighbors", min(30, X.shape[0] - 1))

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        self.model = LocallyLinearEmbedding(n_neighbors=n_neighbors, n_components=n_components, method="standard", **kwargs)
        self.embedding_ = self.model.fit_transform(X_scaled)

        reconstruction_error = self.model.reconstruction_error_

        self.results = {
            "method": "lle",
            "n_components": n_components,
            "embedding": self.embedding_[:, :5].tolist(),
            "n_neighbors": n_neighbors,
            "metrics": {
                "reconstruction_error": round(reconstruction_error, 6),
            },
        }
        return self.results

    def _run_mds(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.manifold import MDS
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        self.model = MDS(n_components=n_components, random_state=42, normalized_stress="auto", **kwargs)
        self.embedding_ = self.model.fit_transform(X_scaled)

        stress = self.model.stress_ if hasattr(self.model, "stress_") else None

        self.results = {
            "method": "mds",
            "n_components": n_components,
            "embedding": self.embedding_[:, :5].tolist(),
            "metrics": {
                "stress": round(stress, 4) if stress is not None else None,
            },
        }
        return self.results

    def _run_tsne(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.manifold import TSNE
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        perplexity = kwargs.pop("perplexity", min(30.0, X.shape[0] - 1))

        self.model = TSNE(n_components=n_components, perplexity=perplexity, random_state=42, **kwargs)
        self.embedding_ = self.model.fit_transform(X_scaled)

        self.results = {
            "method": "tsne",
            "n_components": n_components,
            "embedding": self.embedding_.tolist(),
            "perplexity": perplexity,
            "metrics": {},
        }
        return self.results

    def _run_spectral_embedding(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.manifold import SpectralEmbedding
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        self.model = SpectralEmbedding(n_components=n_components, random_state=42, **kwargs)
        self.embedding_ = self.model.fit_transform(X_scaled)

        self.results = {
            "method": "spectral_embedding",
            "n_components": n_components,
            "embedding": self.embedding_[:, :5].tolist(),
            "metrics": {},
        }
        return self.results

    def _run_locally_linear_embedding(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.manifold import LocallyLinearEmbedding
        from sklearn.preprocessing import StandardScaler

        n_neighbors = kwargs.pop("n_neighbors", min(30, X.shape[0] - 1))

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        self.model = LocallyLinearEmbedding(n_neighbors=n_neighbors, n_components=n_components, method="hessian", **kwargs)
        self.embedding_ = self.model.fit_transform(X_scaled)

        reconstruction_error = self.model.reconstruction_error_

        self.results = {
            "method": "locally_linear_embedding",
            "n_components": n_components,
            "embedding": self.embedding_[:, :5].tolist(),
            "n_neighbors": n_neighbors,
            "metrics": {
                "reconstruction_error": round(reconstruction_error, 6),
            },
        }
        return self.results

    def get_embedding_dataframe(self) -> pd.DataFrame | None:
        """获取嵌入结果DataFrame"""
        if self.embedding_ is None:
            return None
        return pd.DataFrame(self.embedding_, columns=[f"dim_{i}" for i in range(self.embedding_.shape[1])])

    def get_summary(self) -> dict[str, Any]:
        """获取结果摘要"""
        if not self.results:
            return {"status": "error", "message": "Run manifold learning first"}

        return {
            "method": self.results.get("method"),
            "n_components": self.results.get("n_components"),
            "metrics": self.results.get("metrics", {}),
        }