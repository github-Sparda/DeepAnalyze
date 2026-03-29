"""
Regression Runner - 回归分析统一入口

提供多种回归分析算法的统一调用方式。
"""

from __future__ import annotations

from typing import Any, Literal, Optional

import numpy as np
import pandas as pd


class RegressionRunner:
    """
    回归分析统一入口

    支持算法:
    - linear: 线性回归
    - ridge: 岭回归
    - lasso: LASSO回归
    - elastic_net: 弹性网络
    - polynomial: 多项式回归
    - random_forest: 随机森林回归
    - gradient_boosting: 梯度提升回归
    - svr: 支持向量回归
    - mlp: 多层感知机回归
    """

    SUPPORTED_METHODS = ["linear", "ridge", "lasso", "elastic_net", "polynomial", "random_forest", "gradient_boosting", "svr", "mlp"]

    def __init__(self):
        self.results: dict[str, Any] = {}
        self.model: Any = None
        self.feature_importances_: Optional[np.ndarray] = None
        self.coef_: Optional[np.ndarray] = None

    def run(
        self,
        data: pd.DataFrame | np.ndarray,
        y: np.ndarray,
        method: Literal["linear", "ridge", "lasso", "elastic_net", "polynomial", "random_forest", "gradient_boosting", "svr", "mlp", "auto"] = "auto",
        **kwargs,
    ) -> dict[str, Any]:
        """
        运行回归分析

        Args:
            data: 输入数据
            y: 目标变量
            method: 回归算法
            **kwargs: 其他参数

        Returns:
            回归结果
        """
        if isinstance(data, pd.DataFrame):
            X = data.select_dtypes(include=[np.number]).values
            feature_names = data.select_dtypes(include=[np.number]).columns.tolist()
        else:
            X = data
            feature_names = [f"feat_{i}" for i in range(X.shape[1])]

        if method == "auto":
            n_samples, n_features = X.shape
            if n_features > n_samples:
                method = "ridge"
            else:
                method = "linear"

        if method == "linear":
            return self._run_linear(X, y, feature_names, **kwargs)
        elif method == "ridge":
            return self._run_ridge(X, y, feature_names, **kwargs)
        elif method == "lasso":
            return self._run_lasso(X, y, feature_names, **kwargs)
        elif method == "elastic_net":
            return self._run_elastic_net(X, y, feature_names, **kwargs)
        elif method == "polynomial":
            return self._run_polynomial(X, y, feature_names, **kwargs)
        elif method == "random_forest":
            return self._run_random_forest(X, y, feature_names, **kwargs)
        elif method == "gradient_boosting":
            return self._run_gradient_boosting(X, y, feature_names, **kwargs)
        elif method == "svr":
            return self._run_svr(X, y, feature_names, **kwargs)
        elif method == "mlp":
            return self._run_mlp(X, y, feature_names, **kwargs)
        else:
            return {"status": "error", "message": f"Unknown method: {method}"}

    def _run_linear(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.linear_model import LinearRegression
        from sklearn.model_selection import cross_val_score
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

        self.model = LinearRegression(**kwargs)
        self.model.fit(X, y)
        self.coef_ = self.model.coef_

        y_pred = self.model.predict(X)
        cv_scores = cross_val_score(self.model, X, y, cv=min(5, len(y) // 2), scoring="r2")

        coef_df = pd.DataFrame({"feature": feature_names, "coefficient": self.coef_}).sort_values("coefficient", key=abs, ascending=False)

        self.results = {
            "method": "linear",
            "coefficients": coef_df.to_dict(orient="records"),
            "intercept": float(self.model.intercept_),
            "metrics": {
                "r2_score": round(r2_score(y, y_pred), 4),
                "rmse": round(np.sqrt(mean_squared_error(y, y_pred)), 4),
                "mae": round(mean_absolute_error(y, y_pred), 4),
                "cv_r2_mean": round(float(np.mean(cv_scores)), 4),
                "cv_r2_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def _run_ridge(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.linear_model import Ridge
        from sklearn.model_selection import cross_val_score
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        alpha = kwargs.pop("alpha", 1.0)

        self.model = Ridge(alpha=alpha, **kwargs)
        self.model.fit(X_scaled, y)
        self.coef_ = self.model.coef_

        y_pred = self.model.predict(X_scaled)
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=min(5, len(y) // 2), scoring="r2")

        coef_df = pd.DataFrame({"feature": feature_names, "coefficient": self.coef_}).sort_values("coefficient", key=abs, ascending=False)

        self.results = {
            "method": "ridge",
            "alpha": alpha,
            "coefficients": coef_df.to_dict(orient="records"),
            "intercept": float(self.model.intercept_),
            "metrics": {
                "r2_score": round(r2_score(y, y_pred), 4),
                "rmse": round(np.sqrt(mean_squared_error(y, y_pred)), 4),
                "mae": round(mean_absolute_error(y, y_pred), 4),
                "cv_r2_mean": round(float(np.mean(cv_scores)), 4),
                "cv_r2_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def _run_lasso(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.linear_model import Lasso
        from sklearn.model_selection import cross_val_score
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        alpha = kwargs.pop("alpha", 0.1)

        self.model = Lasso(alpha=alpha, max_iter=10000, **kwargs)
        self.model.fit(X_scaled, y)
        self.coef_ = self.model.coef_

        y_pred = self.model.predict(X_scaled)
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=min(5, len(y) // 2), scoring="r2")

        n_nonzero = np.sum(self.coef_ != 0)
        coef_df = pd.DataFrame({"feature": feature_names, "coefficient": self.coef_}).sort_values("coefficient", key=abs, ascending=False)

        self.results = {
            "method": "lasso",
            "alpha": alpha,
            "n_nonzero_features": int(n_nonzero),
            "coefficients": coef_df.to_dict(orient="records"),
            "intercept": float(self.model.intercept_),
            "metrics": {
                "r2_score": round(r2_score(y, y_pred), 4),
                "rmse": round(np.sqrt(mean_squared_error(y, y_pred)), 4),
                "mae": round(mean_absolute_error(y, y_pred), 4),
                "cv_r2_mean": round(float(np.mean(cv_scores)), 4),
                "cv_r2_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def _run_elastic_net(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.linear_model import ElasticNet
        from sklearn.model_selection import cross_val_score
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        alpha = kwargs.pop("alpha", 0.1)
        l1_ratio = kwargs.pop("l1_ratio", 0.5)

        self.model = ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=10000, **kwargs)
        self.model.fit(X_scaled, y)
        self.coef_ = self.model.coef_

        y_pred = self.model.predict(X_scaled)
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=min(5, len(y) // 2), scoring="r2")

        n_nonzero = np.sum(self.coef_ != 0)
        coef_df = pd.DataFrame({"feature": feature_names, "coefficient": self.coef_}).sort_values("coefficient", key=abs, ascending=False)

        self.results = {
            "method": "elastic_net",
            "alpha": alpha,
            "l1_ratio": l1_ratio,
            "n_nonzero_features": int(n_nonzero),
            "coefficients": coef_df.to_dict(orient="records"),
            "intercept": float(self.model.intercept_),
            "metrics": {
                "r2_score": round(r2_score(y, y_pred), 4),
                "rmse": round(np.sqrt(mean_squared_error(y, y_pred)), 4),
                "mae": round(mean_absolute_error(y, y_pred), 4),
                "cv_r2_mean": round(float(np.mean(cv_scores)), 4),
                "cv_r2_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def _run_polynomial(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.preprocessing import PolynomialFeatures
        from sklearn.linear_model import Ridge
        from sklearn.model_selection import cross_val_score
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
        from sklearn.pipeline import Pipeline

        degree = kwargs.pop("degree", 2)

        poly = PolynomialFeatures(degree=degree, include_bias=False)
        X_poly = poly.fit_transform(X)

        alpha = kwargs.pop("alpha", 0.1)

        self.model = Pipeline([("poly", poly), ("ridge", Ridge(alpha=alpha))])
        self.model.fit(X, y)

        y_pred = self.model.predict(X)

        n_features = X_poly.shape[1]
        n_samples = len(y)
        adjusted_r2 = 1 - (1 - r2_score(y, y_pred)) * (n_samples - 1) / (n_samples - n_features - 1)

        self.results = {
            "method": "polynomial",
            "degree": degree,
            "n_features": n_features,
            "metrics": {
                "r2_score": round(r2_score(y, y_pred), 4),
                "adjusted_r2": round(adjusted_r2, 4),
                "rmse": round(np.sqrt(mean_squared_error(y, y_pred)), 4),
                "mae": round(mean_absolute_error(y, y_pred), 4),
            },
        }
        return self.results

    def _run_random_forest(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import cross_val_score
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

        n_estimators = kwargs.pop("n_estimators", 100)
        max_depth = kwargs.pop("max_depth", None)

        self.model = RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42, n_jobs=-1, **kwargs)
        self.model.fit(X, y)
        self.feature_importances_ = self.model.feature_importances_

        y_pred = self.model.predict(X)
        cv_scores = cross_val_score(self.model, X, y, cv=min(5, len(y) // 2), scoring="r2")

        importance_df = pd.DataFrame({"feature": feature_names, "importance": self.feature_importances_}).sort_values("importance", ascending=False)

        self.results = {
            "method": "random_forest",
            "n_estimators": n_estimators,
            "feature_importance": importance_df.head(20).to_dict(orient="records"),
            "metrics": {
                "r2_score": round(r2_score(y, y_pred), 4),
                "rmse": round(np.sqrt(mean_squared_error(y, y_pred)), 4),
                "mae": round(mean_absolute_error(y, y_pred), 4),
                "cv_r2_mean": round(float(np.mean(cv_scores)), 4),
                "cv_r2_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def _run_gradient_boosting(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.model_selection import cross_val_score
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

        n_estimators = kwargs.pop("n_estimators", 100)
        max_depth = kwargs.pop("max_depth", 3)

        self.model = GradientBoostingRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42, **kwargs)
        self.model.fit(X, y)
        self.feature_importances_ = self.model.feature_importances_

        y_pred = self.model.predict(X)
        cv_scores = cross_val_score(self.model, X, y, cv=min(5, len(y) // 2), scoring="r2")

        importance_df = pd.DataFrame({"feature": feature_names, "importance": self.feature_importances_}).sort_values("importance", ascending=False)

        self.results = {
            "method": "gradient_boosting",
            "n_estimators": n_estimators,
            "feature_importance": importance_df.head(20).to_dict(orient="records"),
            "metrics": {
                "r2_score": round(r2_score(y, y_pred), 4),
                "rmse": round(np.sqrt(mean_squared_error(y, y_pred)), 4),
                "mae": round(mean_absolute_error(y, y_pred), 4),
                "cv_r2_mean": round(float(np.mean(cv_scores)), 4),
                "cv_r2_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def _run_svr(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.svm import SVR
        from sklearn.model_selection import cross_val_score
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        C = kwargs.pop("C", 1.0)
        epsilon = kwargs.pop("epsilon", 0.1)

        self.model = SVR(C=C, epsilon=epsilon, **kwargs)
        self.model.fit(X_scaled, y)

        y_pred = self.model.predict(X_scaled)
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=min(5, len(y) // 2), scoring="r2")

        self.results = {
            "method": "svr",
            "C": C,
            "epsilon": epsilon,
            "n_support_vectors": len(self.model.support_vectors_) if hasattr(self.model, "support_vectors_") else None,
            "metrics": {
                "r2_score": round(r2_score(y, y_pred), 4),
                "rmse": round(np.sqrt(mean_squared_error(y, y_pred)), 4),
                "mae": round(mean_absolute_error(y, y_pred), 4),
                "cv_r2_mean": round(float(np.mean(cv_scores)), 4),
                "cv_r2_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def _run_mlp(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.neural_network import MLPRegressor
        from sklearn.model_selection import cross_val_score
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        hidden_layer_sizes = kwargs.pop("hidden_layer_sizes", (100,))

        self.model = MLPRegressor(hidden_layer_sizes=hidden_layer_sizes, max_iter=500, random_state=42, early_stopping=True, **kwargs)
        self.model.fit(X_scaled, y)

        y_pred = self.model.predict(X_scaled)
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=min(5, len(y) // 2), scoring="r2")

        self.results = {
            "method": "mlp",
            "hidden_layer_sizes": hidden_layer_sizes,
            "n_iter_": self.model.n_iter_,
            "metrics": {
                "r2_score": round(r2_score(y, y_pred), 4),
                "rmse": round(np.sqrt(mean_squared_error(y, y_pred)), 4),
                "mae": round(mean_absolute_error(y, y_pred), 4),
                "cv_r2_mean": round(float(np.mean(cv_scores)), 4),
                "cv_r2_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def predict(self, data: pd.DataFrame | np.ndarray) -> np.ndarray:
        """预测"""
        if self.model is None:
            raise ValueError("Run regression first")
        if isinstance(data, pd.DataFrame):
            X = data.select_dtypes(include=[np.number]).values
        else:
            X = data
        return self.model.predict(X)

    def get_summary(self) -> dict[str, Any]:
        """获取结果摘要"""
        if not self.results:
            return {"status": "error", "message": "Run regression first"}

        return {
            "method": self.results.get("method"),
            "metrics": self.results.get("metrics", {}),
        }