"""
Clustering Runner - 聚类分析统一入口

提供多种聚类算法的统一调用方式。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional

import numpy as np
import pandas as pd


class ClusteringRunner:
    """
    聚类分析统一入口

    支持算法:
    - kmeans: K-Means聚类
    - hierarchical: 层次聚类
    - dbscan: DBSCAN密度聚类
    - gmm: 高斯混合模型
    - spectral: 谱聚类
    - birch: BIRCH聚类
    """

    SUPPORTED_METHODS = ["kmeans", "hierarchical", "dbscan", "gmm", "spectral", "birch"]

    def __init__(self):
        self.results: dict[str, Any] = {}
        self.model: Any = None
        self.labels_: Optional[np.ndarray] = None

    def run(
        self,
        data: pd.DataFrame | np.ndarray,
        method: Literal["kmeans", "hierarchical", "dbscan", "gmm", "spectral", "birch", "auto"] = "auto",
        n_clusters: int | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        运行聚类分析

        Args:
            data: 输入数据
            method: 聚类算法
            n_clusters: 聚类数(对于需要的方法)
            **kwargs: 其他参数

        Returns:
            聚类结果
        """
        if isinstance(data, pd.DataFrame):
            X = data.select_dtypes(include=[np.number]).values
            feature_names = data.select_dtypes(include=[np.number]).columns.tolist()
        else:
            X = data
            feature_names = [f"feat_{i}" for i in range(X.shape[1])]

        if method == "auto":
            method = self._auto_select_method(X, n_clusters)

        if method == "kmeans":
            return self._run_kmeans(X, n_clusters, feature_names, **kwargs)
        elif method == "hierarchical":
            return self._run_hierarchical(X, n_clusters, feature_names, **kwargs)
        elif method == "dbscan":
            return self._run_dbscan(X, feature_names, **kwargs)
        elif method == "gmm":
            return self._run_gmm(X, n_clusters, feature_names, **kwargs)
        elif method == "spectral":
            return self._run_spectral(X, n_clusters, feature_names, **kwargs)
        elif method == "birch":
            return self._run_birch(X, n_clusters, feature_names, **kwargs)
        else:
            return {"status": "error", "message": f"Unknown method: {method}"}

    def _auto_select_method(self, X: np.ndarray, n_clusters: int | None) -> str:
        """自动选择最佳聚类方法"""
        n_samples, n_features = X.shape
        if n_samples > 10000:
            return "birch"
        elif n_clusters is None:
            return "hierarchical"
        else:
            return "kmeans"

    def _run_kmeans(
        self, X: np.ndarray, n_clusters: int | None, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score

        if n_clusters is None:
            n_clusters = self._estimate_n_clusters(X, method="elbow")

        self.model = KMeans(n_clusters=n_clusters, random_state=42, **kwargs)
        self.labels_ = self.model.fit_predict(X)

        inertia = self.model.inertia_
        silhouette = silhouette_score(X, self.labels_) if len(np.unique(self.labels_)) > 1 else 0
        calinski = calinski_harabasz_score(X, self.labels_) if len(np.unique(self.labels_)) > 1 else 0
        davies = davies_bouldin_score(X, self.labels_) if len(np.unique(self.labels_)) > 1 else float("inf")

        centers = self.model.cluster_centers_
        center_df = pd.DataFrame(centers, columns=feature_names).to_dict(orient="records")

        self.results = {
            "method": "kmeans",
            "n_clusters": n_clusters,
            "labels": self.labels_.tolist(),
            "centers": center_df,
            "metrics": {
                "inertia": inertia,
                "silhouette_score": round(silhouette, 4),
                "calinski_harabasz_score": round(calinski, 2),
                "davies_bouldin_score": round(davies, 4),
            },
            "cluster_sizes": {int(i): int(np.sum(self.labels_ == i)) for i in range(n_clusters)},
        }
        return self.results

    def _run_hierarchical(
        self, X: np.ndarray, n_clusters: int | None, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.cluster import AgglomerativeClustering
        from scipy.cluster.hierarchy import dendrogram, linkage
        from sklearn.metrics import silhouette_score

        if n_clusters is None:
            n_clusters = self._estimate_n_clusters(X, method="hierarchical")

        self.model = AgglomerativeClustering(n_clusters=n_clusters, **kwargs)
        self.labels_ = self.model.fit_predict(X)

        try:
            Z = linkage(X, method="ward")
            silhouette = silhouette_score(X, self.labels_) if len(np.unique(self.labels_)) > 1 else 0
        except Exception:
            Z = None
            silhouette = 0

        self.results = {
            "method": "hierarchical",
            "n_clusters": n_clusters,
            "labels": self.labels_.tolist(),
            "linkage_matrix": Z.tolist() if Z is not None else None,
            "metrics": {"silhouette_score": round(silhouette, 4)},
            "cluster_sizes": {int(i): int(np.sum(self.labels_ == i)) for i in range(n_clusters)},
        }
        return self.results

    def _run_dbscan(self, X: np.ndarray, feature_names: list[str], **kwargs) -> dict[str, Any]:
        from sklearn.cluster import DBSCAN
        from sklearn.metrics import silhouette_score

        eps = kwargs.pop("eps", 0.5)
        min_samples = kwargs.pop("min_samples", 5)

        self.model = DBSCAN(eps=eps, min_samples=min_samples, **kwargs)
        self.labels_ = self.model.fit_predict(X)

        n_clusters = len(set(self.labels_)) - (1 if -1 in self.labels_ else 0)
        n_noise = list(self.labels_).count(-1)

        if n_clusters > 1 and n_noise < len(self.labels_) * 0.5:
            silhouette = silhouette_score(X, self.labels_)
        else:
            silhouette = 0

        self.results = {
            "method": "dbscan",
            "n_clusters": n_clusters,
            "n_noise": n_noise,
            "labels": self.labels_.tolist(),
            "eps": eps,
            "min_samples": min_samples,
            "metrics": {"silhouette_score": round(silhouette, 4)},
            "cluster_sizes": {
                int(i): int(np.sum(self.labels_ == i))
                for i in set(self.labels_)
                if i != -1
            },
            "noise_size": n_noise,
        }
        return self.results

    def _run_gmm(
        self, X: np.ndarray, n_clusters: int | None, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.mixture import GaussianMixture
        from sklearn.metrics import silhouette_score

        if n_clusters is None:
            n_clusters = self._estimate_n_clusters(X, method="bic")

        self.model = GaussianMixture(n_components=n_clusters, random_state=42, **kwargs)
        self.labels_ = self.model.fit_predict(X)
        probs = self.model.predict_proba(X)

        silhouette = silhouette_score(X, self.labels_) if len(np.unique(self.labels_)) > 1 else 0
        bic = self.model.bic(X)
        aic = self.model.aic(X)

        self.results = {
            "method": "gmm",
            "n_clusters": n_clusters,
            "labels": self.labels_.tolist(),
            "probabilities": probs[:, :3].tolist(),
            "metrics": {
                "silhouette_score": round(silhouette, 4),
                "bic": round(bic, 2),
                "aic": round(aic, 2),
            },
            "cluster_sizes": {int(i): int(np.sum(self.labels_ == i)) for i in range(n_clusters)},
        }
        return self.results

    def _run_spectral(
        self, X: np.ndarray, n_clusters: int | None, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.cluster import SpectralClustering
        from sklearn.metrics import silhouette_score

        if n_clusters is None:
            n_clusters = self._estimate_n_clusters(X, method="elbow")

        self.model = SpectralClustering(n_clusters=n_clusters, random_state=42, **kwargs)
        self.labels_ = self.model.fit_predict(X)

        silhouette = silhouette_score(X, self.labels_) if len(np.unique(self.labels_)) > 1 else 0

        self.results = {
            "method": "spectral",
            "n_clusters": n_clusters,
            "labels": self.labels_.tolist(),
            "metrics": {"silhouette_score": round(silhouette, 4)},
            "cluster_sizes": {int(i): int(np.sum(self.labels_ == i)) for i in range(n_clusters)},
        }
        return self.results

    def _run_birch(
        self, X: np.ndarray, n_clusters: int | None, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.cluster import Birch
        from sklearn.metrics import silhouette_score

        if n_clusters is None:
            n_clusters = self._estimate_n_clusters(X, method="elbow")

        self.model = Birch(n_clusters=n_clusters, **kwargs)
        self.labels_ = self.model.fit_predict(X)

        silhouette = silhouette_score(X, self.labels_) if len(np.unique(self.labels_)) > 1 else 0

        self.results = {
            "method": "birch",
            "n_clusters": n_clusters,
            "labels": self.labels_.tolist(),
            "metrics": {"silhouette_score": round(silhouette, 4)},
            "cluster_sizes": {int(i): int(np.sum(self.labels_ == i)) for i in range(n_clusters)},
        }
        return self.results

    def _estimate_n_clusters(self, X: np.ndarray, method: str = "elbow") -> int:
        """估计最佳聚类数"""
        if method == "elbow":
            from sklearn.cluster import KMeans

            inertias = []
            silhouettes = []
            K_range = range(2, min(11, len(X)))
            for k in K_range:
                km = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = km.fit_predict(X)
                from sklearn.metrics import silhouette_score
                silhouettes.append(silhouette_score(X, labels))
                inertias.append(km.inertia_)

            self._cluster_evaluation = {
                "K_range": list(K_range),
                "inertias": inertias,
                "silhouettes": silhouettes,
            }
            best_k = list(K_range)[np.argmax(silhouettes)]
            return int(best_k)
        elif method == "hierarchical":
            from sklearn.cluster import AgglomerativeClustering
            from sklearn.metrics import silhouette_score

            silhouettes = []
            K_range = range(2, min(11, len(X)))
            for k in K_range:
                ac = AgglomerativeClustering(n_clusters=k)
                labels = ac.fit_predict(X)
                silhouettes.append(silhouette_score(X, labels))

            best_k = list(K_range)[np.argmax(silhouettes)]
            return int(best_k)
        elif method == "bic":
            from sklearn.mixture import GaussianMixture

            bics = []
            K_range = range(2, min(11, len(X)))
            for k in K_range:
                gmm = GaussianMixture(n_components=k, random_state=42)
                gmm.fit(X)
                bics.append(gmm.bic(X))

            best_k = list(K_range)[np.argmin(bics)]
            return int(best_k)
        else:
            return 3

    def get_cluster_profiles(self, data: pd.DataFrame) -> dict[str, Any]:
        """获取每个聚类的特征画像"""
        if self.labels_ is None:
            return {"status": "error", "message": "Run clustering first"}

        df = data.copy()
        df["_cluster"] = self.labels_

        profiles = {}
        for cluster_id in sorted(set(self.labels_)):
            cluster_data = df[df["_cluster"] == cluster_id].drop(columns=["_cluster"])
            numeric_cols = cluster_data.select_dtypes(include=[np.number])

            profiles[f"cluster_{cluster_id}"] = {
                "size": int(np.sum(self.labels_ == cluster_id)),
                "means": numeric_cols.mean().to_dict(),
                "stds": numeric_cols.std().to_dict(),
            }

        return profiles

    def get_summary(self) -> dict[str, Any]:
        """获取结果摘要"""
        if not self.results:
            return {"status": "error", "message": "Run clustering first"}

        return {
            "method": self.results.get("method"),
            "n_clusters": self.results.get("n_clusters"),
            "metrics": self.results.get("metrics", {}),
            "cluster_sizes": self.results.get("cluster_sizes", {}),
        }
