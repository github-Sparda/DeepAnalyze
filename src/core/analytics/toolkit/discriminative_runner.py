"""
Discriminative Runner - 判别式机器学习统一入口

提供多种判别式ML算法的统一调用方式。
"""

from __future__ import annotations

from typing import Any, Literal, Optional

import numpy as np
import pandas as pd


class DiscriminativeRunner:
    """
    判别式机器学习统一入口

    支持算法:
    - logistic_regression: 逻辑回归
    - svm: 支持向量机
    - random_forest: 随机森林
    - gradient_boosting: 梯度提升树
    - xgboost: XGBoost
    - lightgbm: LightGBM
    - mlp: 多层感知机
    """

    SUPPORTED_METHODS = ["logistic_regression", "svm", "random_forest", "gradient_boosting", "xgboost", "lightgbm", "mlp"]

    def __init__(self):
        self.results: dict[str, Any] = {}
        self.model: Any = None
        self.feature_importances_: Optional[np.ndarray] = None
        self.classes_: Optional[np.ndarray] = None

    def run(
        self,
        data: pd.DataFrame | np.ndarray,
        y: np.ndarray,
        method: Literal["logistic_regression", "svm", "random_forest", "gradient_boosting", "xgboost", "lightgbm", "mlp", "auto"] = "auto",
        **kwargs,
    ) -> dict[str, Any]:
        """
        运行判别式ML分类

        Args:
            data: 输入数据
            y: 标签
            method: 分类算法
            **kwargs: 其他参数

        Returns:
            分类结果
        """
        if isinstance(data, pd.DataFrame):
            X = data.select_dtypes(include=[np.number]).values
            feature_names = data.select_dtypes(include=[np.number]).columns.tolist()
        else:
            X = data
            feature_names = [f"feat_{i}" for i in range(X.shape[1])]

        self.classes_ = np.unique(y)

        if method == "auto":
            n_samples, n_features = X.shape
            n_classes = len(self.classes_)
            if n_samples < 1000:
                method = "svm" if n_classes == 2 else "random_forest"
            else:
                method = "random_forest"

        if method == "logistic_regression":
            return self._run_logistic_regression(X, y, feature_names, **kwargs)
        elif method == "svm":
            return self._run_svm(X, y, feature_names, **kwargs)
        elif method == "random_forest":
            return self._run_random_forest(X, y, feature_names, **kwargs)
        elif method == "gradient_boosting":
            return self._run_gradient_boosting(X, y, feature_names, **kwargs)
        elif method == "xgboost":
            return self._run_xgboost(X, y, feature_names, **kwargs)
        elif method == "lightgbm":
            return self._run_lightgbm(X, y, feature_names, **kwargs)
        elif method == "mlp":
            return self._run_mlp(X, y, feature_names, **kwargs)
        else:
            return {"status": "error", "message": f"Unknown method: {method}"}

    def _run_logistic_regression(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import cross_val_score
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        C = kwargs.pop("C", 1.0)
        max_iter = kwargs.pop("max_iter", 1000)

        self.model = LogisticRegression(C=C, max_iter=max_iter, random_state=42, **kwargs)
        self.model.fit(X_scaled, y)

        cv_scores = cross_val_score(self.model, X_scaled, y, cv=min(5, len(np.unique(y)) * 2))
        accuracy = cross_val_score(self.model, X_scaled, y, cv=min(5, len(np.unique(y)) * 2), scoring="accuracy")
        f1 = cross_val_score(self.model, X_scaled, y, cv=min(5, len(np.unique(y)) * 2), scoring="f1_weighted")

        coef_df = pd.DataFrame(self.model.coef_, columns=feature_names, index=[f"class_{i}" for i in range(self.model.coef_.shape[0])])

        self.results = {
            "method": "logistic_regression",
            "classes": self.classes_.tolist(),
            "coefficients": coef_df.to_dict(orient="index"),
            "intercept": self.model.intercept_.tolist(),
            "metrics": {
                "cv_accuracy_mean": round(float(np.mean(cv_scores)), 4),
                "cv_accuracy_std": round(float(np.std(cv_scores)), 4),
                "cv_f1_mean": round(float(np.mean(f1)), 4),
            },
        }
        return self.results

    def _run_svm(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.svm import SVC
        from sklearn.model_selection import cross_val_score
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        C = kwargs.pop("C", 1.0)
        kernel = kwargs.pop("kernel", "rbf")

        self.model = SVC(C=C, kernel=kernel, random_state=42, probability=True, **kwargs)
        self.model.fit(X_scaled, y)

        cv_scores = cross_val_score(self.model, X_scaled, y, cv=min(5, len(np.unique(y)) * 2))

        self.results = {
            "method": "svm",
            "classes": self.classes_.tolist(),
            "support_vectors": self.model.support_vectors_.shape[0],
            "n_support_vectors": self.model.n_support_.tolist(),
            "metrics": {
                "cv_accuracy_mean": round(float(np.mean(cv_scores)), 4),
                "cv_accuracy_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def _run_random_forest(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score

        n_estimators = kwargs.pop("n_estimators", 100)
        max_depth = kwargs.pop("max_depth", None)

        self.model = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42, n_jobs=-1, **kwargs)
        self.model.fit(X, y)

        cv_scores = cross_val_score(self.model, X, y, cv=min(5, len(np.unique(y)) * 2))
        self.feature_importances_ = self.model.feature_importances_

        importance_df = pd.DataFrame({"feature": feature_names, "importance": self.feature_importances_}).sort_values("importance", ascending=False)

        self.results = {
            "method": "random_forest",
            "classes": self.classes_.tolist(),
            "n_estimators": n_estimators,
            "feature_importance": importance_df.head(20).to_dict(orient="records"),
            "metrics": {
                "cv_accuracy_mean": round(float(np.mean(cv_scores)), 4),
                "cv_accuracy_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def _run_gradient_boosting(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.model_selection import cross_val_score

        n_estimators = kwargs.pop("n_estimators", 100)
        max_depth = kwargs.pop("max_depth", 3)

        self.model = GradientBoostingClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42, **kwargs)
        self.model.fit(X, y)

        cv_scores = cross_val_score(self.model, X, y, cv=min(5, len(np.unique(y)) * 2))
        self.feature_importances_ = self.model.feature_importances_

        importance_df = pd.DataFrame({"feature": feature_names, "importance": self.feature_importances_}).sort_values("importance", ascending=False)

        self.results = {
            "method": "gradient_boosting",
            "classes": self.classes_.tolist(),
            "n_estimators": n_estimators,
            "feature_importance": importance_df.head(20).to_dict(orient="records"),
            "metrics": {
                "cv_accuracy_mean": round(float(np.mean(cv_scores)), 4),
                "cv_accuracy_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def _run_xgboost(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        try:
            import xgboost as xgb
            from sklearn.model_selection import cross_val_score
        except ImportError:
            return {"status": "error", "message": "xgboost not installed"}

        n_estimators = kwargs.pop("n_estimators", 100)
        max_depth = kwargs.pop("max_depth", 6)

        self.model = xgb.XGBClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42, use_label_encoder=False, eval_metric="logloss", **kwargs)
        self.model.fit(X, y)

        cv_scores = cross_val_score(self.model, X, y, cv=min(5, len(np.unique(y)) * 2))
        self.feature_importances_ = self.model.feature_importances_

        importance_df = pd.DataFrame({"feature": feature_names, "importance": self.feature_importances_}).sort_values("importance", ascending=False)

        self.results = {
            "method": "xgboost",
            "classes": self.classes_.tolist(),
            "n_estimators": n_estimators,
            "feature_importance": importance_df.head(20).to_dict(orient="records"),
            "metrics": {
                "cv_accuracy_mean": round(float(np.mean(cv_scores)), 4),
                "cv_accuracy_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def _run_lightgbm(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        try:
            import lightgbm as lgb
            from sklearn.model_selection import cross_val_score
        except ImportError:
            return {"status": "error", "message": "lightgbm not installed"}

        n_estimators = kwargs.pop("n_estimators", 100)

        self.model = lgb.LGBMClassifier(n_estimators=n_estimators, random_state=42, verbose=-1, **kwargs)
        self.model.fit(X, y)

        cv_scores = cross_val_score(self.model, X, y, cv=min(5, len(np.unique(y)) * 2))
        self.feature_importances_ = self.model.feature_importances_

        importance_df = pd.DataFrame({"feature": feature_names, "importance": self.feature_importances_}).sort_values("importance", ascending=False)

        self.results = {
            "method": "lightgbm",
            "classes": self.classes_.tolist(),
            "n_estimators": n_estimators,
            "feature_importance": importance_df.head(20).to_dict(orient="records"),
            "metrics": {
                "cv_accuracy_mean": round(float(np.mean(cv_scores)), 4),
                "cv_accuracy_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def _run_mlp(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str], **kwargs
    ) -> dict[str, Any]:
        from sklearn.neural_network import MLPClassifier
        from sklearn.model_selection import cross_val_score
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        hidden_layer_sizes = kwargs.pop("hidden_layer_sizes", (100,))

        self.model = MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, max_iter=500, random_state=42, early_stopping=True, **kwargs)
        self.model.fit(X_scaled, y)

        cv_scores = cross_val_score(self.model, X_scaled, y, cv=min(5, len(np.unique(y)) * 2))

        self.results = {
            "method": "mlp",
            "classes": self.classes_.tolist(),
            "hidden_layer_sizes": hidden_layer_sizes,
            "n_iter_": self.model.n_iter_,
            "metrics": {
                "cv_accuracy_mean": round(float(np.mean(cv_scores)), 4),
                "cv_accuracy_std": round(float(np.std(cv_scores)), 4),
            },
        }
        return self.results

    def predict(self, data: pd.DataFrame | np.ndarray) -> np.ndarray:
        """预测"""
        if self.model is None:
            raise ValueError("Run classification first")
        if isinstance(data, pd.DataFrame):
            X = data.select_dtypes(include=[np.number]).values
        else:
            X = data
        return self.model.predict(X)

    def predict_proba(self, data: pd.DataFrame | np.ndarray) -> np.ndarray:
        """预测概率"""
        if self.model is None:
            raise ValueError("Run classification first")
        if isinstance(data, pd.DataFrame):
            X = data.select_dtypes(include=[np.number]).values
        else:
            X = data
        return self.model.predict_proba(X)

    def get_summary(self) -> dict[str, Any]:
        """获取结果摘要"""
        if not self.results:
            return {"status": "error", "message": "Run classification first"}

        return {
            "method": self.results.get("method"),
            "classes": self.results.get("classes"),
            "metrics": self.results.get("metrics", {}),
        }