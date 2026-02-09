"""
Machine Learning Pipeline for DeepAnalyze
Provides automated model selection, training, and optimization capabilities
"""

from __future__ import annotations

import json
import warnings
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, mean_squared_error, r2_score, classification_report
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    warnings.warn("XGBoost not available. Install with: pip install xgboost")

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    warnings.warn("LightGBM not available. Install with: pip install lightgbm")


class MLPipeline:
    """
    Automated Machine Learning Pipeline
    Handles model selection, training, validation, and hyperparameter optimization
    """
    
    def __init__(self, task_type: str = "auto", random_state: int = 42):
        """
        Initialize ML Pipeline
        
        Args:
            task_type: "classification", "regression", or "auto" for automatic detection
            random_state: Random seed for reproducibility
        """
        self.task_type = task_type
        self.random_state = random_state
        self.models = {}
        self.best_model = None
        self.best_score = None
        self.feature_names = None
        self.preprocessor = None
        self.is_fitted = False
        
    def detect_task_type(self, y: pd.Series) -> str:
        """Automatically detect if task is classification or regression"""
        if y.dtype in ['object', 'category'] or y.nunique() <= 20:
            return "classification"
        else:
            return "regression"
    
    def prepare_data(self, X: pd.DataFrame, y: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for ML training with proper preprocessing"""
        # Store feature names
        self.feature_names = X.columns.tolist()
        
        # Identify categorical and numerical columns
        categorical_features = X.select_dtypes(include=['object', 'category']).columns.tolist()
        numerical_features = X.select_dtypes(include=['int64', 'float64']).columns.tolist()
        
        # Create preprocessing pipeline
        if categorical_features:
            preprocessor = ColumnTransformer(
                transformers=[
                    ('num', StandardScaler(), numerical_features),
                    ('cat', OneHotEncoder(drop='first', sparse_output=False), categorical_features)
                ]
            )
        else:
            preprocessor = StandardScaler()
            
        self.preprocessor = preprocessor
        
        # Transform data
        X_processed = preprocessor.fit_transform(X)
        y_processed = y.values
        
        return X_processed, y_processed
    
    def get_candidate_models(self) -> Dict[str, Any]:
        """Get candidate models based on task type"""
        if self.task_type == "classification":
            models = {
                'logistic_regression': LogisticRegression(random_state=self.random_state),
                'random_forest': RandomForestClassifier(random_state=self.random_state),
                'decision_tree': DecisionTreeClassifier(random_state=self.random_state),
            }
            
            if XGBOOST_AVAILABLE:
                models['xgboost'] = xgb.XGBClassifier(random_state=self.random_state)
            
            if LIGHTGBM_AVAILABLE:
                models['lightgbm'] = lgb.LGBMClassifier(random_state=self.random_state)
                
        else:  # regression
            models = {
                'linear_regression': LinearRegression(),
                'random_forest': RandomForestRegressor(random_state=self.random_state),
                'decision_tree': DecisionTreeRegressor(random_state=self.random_state),
            }
            
            if XGBOOST_AVAILABLE:
                models['xgboost'] = xgb.XGBRegressor(random_state=self.random_state)
            
            if LIGHTGBM_AVAILABLE:
                models['lightgbm'] = lgb.LGBMRegressor(random_state=self.random_state)
        
        return models
    
    def evaluate_models(self, X_train: np.ndarray, X_test: np.ndarray, 
                       y_train: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """Evaluate all candidate models"""
        models = self.get_candidate_models()
        scores = {}
        
        for name, model in models.items():
            try:
                # Train model
                model.fit(X_train, y_train)
                
                # Predict
                if self.task_type == "classification":
                    y_pred = model.predict(X_test)
                    score = accuracy_score(y_test, y_pred)
                else:
                    y_pred = model.predict(X_test)
                    score = r2_score(y_test, y_pred)
                
                scores[name] = score
                self.models[name] = model
                
            except Exception as e:
                print(f"Error training {name}: {e}")
                scores[name] = 0.0
        
        return scores
    
    def optimize_hyperparameters(self, X: np.ndarray, y: np.ndarray, 
                                model_name: str, cv: int = 3) -> Any:
        """Optimize hyperparameters for a specific model"""
        model = self.models[model_name]
        
        # Define parameter grids
        param_grids = {
            'logistic_regression': {
                'C': [0.1, 1, 10, 100],
                'penalty': ['l1', 'l2'],
                'solver': ['liblinear']
            },
            'random_forest': {
                'n_estimators': [50, 100, 200],
                'max_depth': [None, 10, 20, 30],
                'min_samples_split': [2, 5, 10]
            },
            'decision_tree': {
                'max_depth': [None, 10, 20, 30],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            }
        }
        
        if XGBOOST_AVAILABLE and model_name == 'xgboost':
            param_grids['xgboost'] = {
                'n_estimators': [50, 100, 200],
                'max_depth': [3, 6, 9],
                'learning_rate': [0.01, 0.1, 0.2]
            }
        
        if LIGHTGBM_AVAILABLE and model_name == 'lightgbm':
            param_grids['lightgbm'] = {
                'n_estimators': [50, 100, 200],
                'max_depth': [3, 6, 9],
                'learning_rate': [0.01, 0.1, 0.2]
            }
        
        if model_name not in param_grids:
            return model
        
        # Perform grid search
        grid_search = GridSearchCV(
            model, 
            param_grids[model_name], 
            cv=cv, 
            scoring='accuracy' if self.task_type == 'classification' else 'r2',
            n_jobs=-1
        )
        
        grid_search.fit(X, y)
        return grid_search.best_estimator_
    
    def fit(self, X: pd.DataFrame, y: pd.Series, 
            test_size: float = 0.2, optimize: bool = True) -> Dict[str, Any]:
        """
        Fit the ML pipeline
        
        Args:
            X: Feature DataFrame
            y: Target Series
            test_size: Proportion of data for testing
            optimize: Whether to perform hyperparameter optimization
            
        Returns:
            Dictionary with evaluation results
        """
        # Detect task type if auto
        if self.task_type == "auto":
            self.task_type = self.detect_task_type(y)
        
        # Prepare data
        X_processed, y_processed = self.prepare_data(X, y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_processed, y_processed, test_size=test_size, random_state=self.random_state
        )
        
        # Evaluate models
        scores = self.evaluate_models(X_train, X_test, y_train, y_test)
        
        # Find best model
        self.best_model_name = max(scores, key=scores.get)
        self.best_score = scores[self.best_model_name]
        self.best_model = self.models[self.best_model_name]
        
        # Optimize hyperparameters if requested
        if optimize and len(X) > 100:  # Only optimize for larger datasets
            try:
                self.best_model = self.optimize_hyperparameters(X_processed, y_processed, self.best_model_name)
                # Re-evaluate optimized model
                self.best_model.fit(X_train, y_train)
                if self.task_type == "classification":
                    y_pred = self.best_model.predict(X_test)
                    self.best_score = accuracy_score(y_test, y_pred)
                else:
                    y_pred = self.best_model.predict(X_test)
                    self.best_score = r2_score(y_test, y_pred)
            except Exception as e:
                print(f"Hyperparameter optimization failed: {e}")
        
        self.is_fitted = True
        
        return {
            'model_scores': scores,
            'best_model': self.best_model_name,
            'best_score': self.best_score,
            'task_type': self.task_type
        }
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions on new data"""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        X_processed = self.preprocessor.transform(X)
        return self.best_model.predict(X_processed)
    
    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """Get feature importance if available"""
        if not self.is_fitted:
            return None
            
        if hasattr(self.best_model, 'feature_importances_'):
            importance = self.best_model.feature_importances_
            feature_names = self._get_feature_names_after_preprocessing()
            return pd.DataFrame({
                'feature': feature_names,
                'importance': importance
            }).sort_values('importance', ascending=False)
        elif hasattr(self.best_model, 'coef_'):
            coef = np.abs(self.best_model.coef_[0]) if self.best_model.coef_.ndim > 1 else np.abs(self.best_model.coef_)
            feature_names = self._get_feature_names_after_preprocessing()
            return pd.DataFrame({
                'feature': feature_names,
                'importance': coef
            }).sort_values('importance', ascending=False)
        else:
            return None
    
    def _get_feature_names_after_preprocessing(self) -> List[str]:
        """Get feature names after preprocessing (handling one-hot encoding)"""
        if hasattr(self.preprocessor, 'get_feature_names_out'):
            return self.preprocessor.get_feature_names_out().tolist()
        elif hasattr(self.preprocessor, 'named_transformers_'):
            # Handle ColumnTransformer
            feature_names = []
            for name, transformer, features in self.preprocessor.transformers_:
                if name != 'remainder':
                    if hasattr(transformer, 'get_feature_names_out'):
                        transformed_names = transformer.get_feature_names_out(features)
                        feature_names.extend(transformed_names)
                    else:
                        feature_names.extend(features)
            return feature_names
        else:
            return self.feature_names or [f"feature_{i}" for i in range(len(self.feature_names or []))]
    
    def generate_model_report(self) -> Dict[str, Any]:
        """Generate comprehensive model performance report"""
        if not self.is_fitted:
            return {"error": "Model not fitted"}
        
        report = {
            'task_type': self.task_type,
            'best_model': self.best_model_name,
            'best_score': float(self.best_score),
            'feature_importance': None
        }
        
        # Add feature importance
        importance_df = self.get_feature_importance()
        if importance_df is not None:
            report['feature_importance'] = importance_df.head(10).to_dict('records')
        
        return report


class FeatureEngineer:
    """Automated feature engineering and selection"""
    
    def __init__(self):
        self.selected_features = None
        self.scaler = StandardScaler()
    
    def engineer_features(self, df: pd.DataFrame, target_column: str) -> pd.DataFrame:
        """Perform automated feature engineering"""
        df_processed = df.copy()
        
        # Handle missing values
        for col in df_processed.columns:
            if df_processed[col].isnull().sum() > 0:
                if df_processed[col].dtype in ['int64', 'float64']:
                    df_processed[col] = df_processed[col].fillna(df_processed[col].median())
                else:
                    df_processed[col] = df_processed[col].fillna(df_processed[col].mode()[0] if not df_processed[col].mode().empty else 'Unknown')
        
        # Create interaction features for numerical columns
        numerical_cols = df_processed.select_dtypes(include=['int64', 'float64']).columns
        numerical_cols = [col for col in numerical_cols if col != target_column]
        
        if len(numerical_cols) > 1:
            for i in range(min(3, len(numerical_cols))):
                for j in range(i+1, min(5, len(numerical_cols))):
                    col1, col2 = numerical_cols[i], numerical_cols[j]
                    df_processed[f'{col1}_x_{col2}'] = df_processed[col1] * df_processed[col2]
                    df_processed[f'{col1}_plus_{col2}'] = df_processed[col1] + df_processed[col2]
        
        # Create polynomial features for key numerical columns
        key_numerical = numerical_cols[:2]  # Top 2 numerical columns
        for col in key_numerical:
            df_processed[f'{col}_squared'] = df_processed[col] ** 2
            df_processed[f'{col}_sqrt'] = np.sqrt(np.abs(df_processed[col]))
        
        return df_processed
    
    def select_features(self, X: pd.DataFrame, y: pd.Series, k: int = 10) -> List[str]:
        """Select top k features using correlation and variance"""
        # Remove constant features
        X_var = X.var()
        X_filtered = X.loc[:, X_var > 0]
        
        if len(X_filtered.columns) <= k:
            self.selected_features = X_filtered.columns.tolist()
            return self.selected_features
        
        # Select based on correlation with target (for numerical targets)
        if y.dtype in ['int64', 'float64']:
            correlations = X_filtered.corrwith(y).abs().sort_values(ascending=False)
            self.selected_features = correlations.head(k).index.tolist()
        else:
            # For categorical targets, use different approach
            from sklearn.feature_selection import SelectKBest, f_classif
            selector = SelectKBest(score_func=f_classif, k=min(k, len(X_filtered.columns)))
            selector.fit(X_filtered, y)
            self.selected_features = X_filtered.columns[selector.get_support()].tolist()
        
        return self.selected_features


# 导出主要类
__all__ = ['MLPipeline', 'FeatureEngineer']