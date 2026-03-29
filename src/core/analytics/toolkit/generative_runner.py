"""
Generative Runner - 生成式机器学习统一入口

提供多种生成式ML算法的统一调用方式。
"""

from __future__ import annotations

from typing import Any, Literal, Optional

import numpy as np
import pandas as pd


class GenerativeRunner:
    """
    生成式机器学习统一入口

    支持算法:
    - vae: 变分自编码器
    - gmm: 高斯混合模型(生成式)
    - pca: 主成分分析(生成式)
    - factor_analysis: 因子分析(生成式)
    - nmf: 非负矩阵分解(生成式)
    """

    SUPPORTED_METHODS = ["vae", "gmm", "pca", "factor_analysis", "nmf"]

    def __init__(self):
        self.results: dict[str, Any] = {}
        self.model: Any = None
        self.embedding_: Optional[np.ndarray] = None
        self.classes_: Optional[np.ndarray] = None

    def run(
        self,
        data: pd.DataFrame | np.ndarray,
        method: Literal["vae", "gmm", "pca", "factor_analysis", "nmf", "auto"] = "auto",
        n_components: int | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        运行生成式ML分析

        Args:
            data: 输入数据
            method: 生成式算法
            n_components: 隐变量/成分数
            **kwargs: 其他参数

        Returns:
            生成式ML结果
        """
        if isinstance(data, pd.DataFrame):
            X = data.select_dtypes(include=[np.number]).values
            feature_names = data.select_dtypes(include=[np.number]).columns.tolist()
        else:
            X = data
            feature_names = [f"feat_{i}" for i in range(X.shape[1])]

        if n_components is None:
            n_components = min(10, X.shape[1], X.shape[0] // 2)

        if method == "auto":
            method = "pca"

        if method == "vae":
            return self._run_vae(X, n_components, feature_names, **kwargs)
        elif method == "gmm":
            return self._run_gmm(X, n_components, feature_names, **kwargs)
        elif method == "pca":
            return self._run_pca(X, n_components, feature_names, **kwargs)
        elif method == "factor_analysis":
            return self._run_factor_analysis(X, n_components, feature_names, **kwargs)
        elif method == "nmf":
            return self._run_nmf(X, n_components, feature_names, **kwargs)
        else:
            return {"status": "error", "message": f"Unknown method: {method}"}

    def _run_vae(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader, TensorDataset
        except ImportError:
            return {"status": "error", "message": "torch not installed"}

        input_dim = X.shape[1]
        hidden_dim = kwargs.pop("hidden_dim", 256)
        latent_dim = n_components
        epochs = kwargs.pop("epochs", 100)
        batch_size = kwargs.pop("batch_size", 64)
        learning_rate = kwargs.pop("learning_rate", 0.001)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        class Encoder(nn.Module):
            def __init__(self, input_dim, hidden_dim, latent_dim):
                super().__init__()
                self.fc1 = nn.Linear(input_dim, hidden_dim)
                self.fc_mu = nn.Linear(hidden_dim, latent_dim)
                self.fc_logvar = nn.Linear(hidden_dim, latent_dim)

            def forward(self, x):
                h = torch.relu(self.fc1(x))
                mu = self.fc_mu(h)
                logvar = self.fc_logvar(h)
                return mu, logvar

        class Decoder(nn.Module):
            def __init__(self, latent_dim, hidden_dim, output_dim):
                super().__init__()
                self.fc1 = nn.Linear(latent_dim, hidden_dim)
                self.fc2 = nn.Linear(hidden_dim, output_dim)

            def forward(self, z):
                h = torch.relu(self.fc1(z))
                return self.fc2(h)

        class VAE(nn.Module):
            def __init__(self, input_dim, hidden_dim, latent_dim):
                super().__init__()
                self.encoder = Encoder(input_dim, hidden_dim, latent_dim)
                self.decoder = Decoder(latent_dim, hidden_dim, input_dim)

            def reparameterize(self, mu, logvar):
                std = torch.exp(0.5 * logvar)
                eps = torch.randn_like(std)
                return mu + eps * std

            def forward(self, x):
                mu, logvar = self.encoder(x)
                z = self.reparameterize(mu, logvar)
                return self.decoder(z), mu, logvar

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        vae = VAE(input_dim, hidden_dim, latent_dim).to(device)
        optimizer = torch.optim.Adam(vae.parameters(), lr=learning_rate)

        X_tensor = torch.FloatTensor(X_scaled)
        dataset = TensorDataset(X_tensor)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        for epoch in range(epochs):
            for batch in dataloader:
                x = batch[0].to(device)
                recon, mu, logvar = vae(x)
                recon_loss = nn.functional.mse_loss(recon, x, reduction="sum")
                kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
                loss = recon_loss + kl_loss
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

        vae.eval()
        with torch.no_grad():
            mu, _ = vae.encoder(X_tensor.to(device))
            self.embedding_ = mu.cpu().numpy()

        self.model = vae
        self.results = {
            "method": "vae",
            "n_components": latent_dim,
            "embedding": self.embedding_[:, :5].tolist(),
            "epochs": epochs,
            "metrics": {},
        }
        return self.results

    def _run_gmm(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.mixture import GaussianMixture
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        self.model = GaussianMixture(n_components=n_components, random_state=42, **kwargs)
        self.model.fit(X_scaled)

        self.embedding_ = self.model.sample(n_samples=min(100, X.shape[0]))[0]

        bic = self.model.bic(X_scaled)
        aic = self.model.aic(X_scaled)

        self.results = {
            "method": "gmm",
            "n_components": n_components,
            "generated_samples": self.embedding_[:5].tolist(),
            "metrics": {
                "bic": round(bic, 2),
                "aic": round(aic, 2),
            },
        }
        return self.results

    def _run_pca(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        self.model = PCA(n_components=n_components, **kwargs)
        self.embedding_ = self.model.fit_transform(X_scaled)

        reconstructed = self.model.inverse_transform(self.embedding_)
        mse = np.mean((X_scaled - reconstructed) ** 2)

        self.results = {
            "method": "pca",
            "n_components": n_components,
            "embedding": self.embedding_[:5].tolist(),
            "explained_variance_ratio": self.model.explained_variance_ratio_.tolist(),
            "metrics": {
                "reconstruction_mse": round(mse, 6),
                "total_variance_explained": round(float(np.sum(self.model.explained_variance_ratio_)), 4),
            },
        }
        return self.results

    def _run_factor_analysis(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.decomposition import FactorAnalysis
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        self.model = FactorAnalysis(n_components=n_components, random_state=42, **kwargs)
        self.embedding_ = self.model.fit_transform(X_scaled)

        reconstructed = self.model.inverse_transform(self.embedding_)
        mse = np.mean((X_scaled - reconstructed) ** 2)

        self.results = {
            "method": "factor_analysis",
            "n_components": n_components,
            "embedding": self.embedding_[:5].tolist(),
            "metrics": {
                "reconstruction_mse": round(mse, 6),
            },
        }
        return self.results

    def _run_nmf(
        self, X: np.ndarray, n_components: int, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.decomposition import NMF

        X_pos = X - X.min() + 1e-6

        self.model = NMF(n_components=n_components, random_state=42, max_iter=500, **kwargs)
        self.embedding_ = self.model.fit_transform(X_pos)

        reconstructed = self.model.inverse_transform(self.embedding_)
        mse = np.mean((X_pos - reconstructed) ** 2)

        self.results = {
            "method": "nmf",
            "n_components": n_components,
            "embedding": self.embedding_[:5].tolist(),
            "components": self.model.components_[:3].tolist(),
            "metrics": {
                "reconstruction_mse": round(mse, 6),
            },
        }
        return self.results

    def generate(self, n_samples: int = 100) -> np.ndarray:
        """生成新样本"""
        if self.model is None:
            raise ValueError("Run generative model first")

        method = self.results.get("method")

        if method == "vae":
            import torch
            device = next(self.model.parameters()).device
            z = torch.randn(n_samples, self.model.encoder.fc_mu.out_features).to(device)
            with torch.no_grad():
                generated = self.model.decoder(z).cpu().numpy()
            return generated
        elif method == "gmm":
            return self.model.sample(n_samples)[0]
        else:
            raise NotImplementedError(f"Generate not implemented for {method}")

    def get_summary(self) -> dict[str, Any]:
        """获取结果摘要"""
        if not self.results:
            return {"status": "error", "message": "Run generative model first"}

        return {
            "method": self.results.get("method"),
            "n_components": self.results.get("n_components"),
            "metrics": self.results.get("metrics", {}),
        }