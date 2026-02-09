"""
Feature Engineering Module for DeepAnalyze
Provides automated feature selection, transformation, and engineering capabilities
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder, OneHotEncoder
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_classif, f_regression, mutual_info_classif, mutual_info_regression


class AutomatedFeatureEngineer:
    """
    Automated feature engineering system that handles:
    - Missing value imputation
    - Feature scaling and normalization
    - Encoding categorical variables
    - Creating interaction features
    - Dimensionality reduction
    - Feature selection
    """
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.scalers = {}
        self.encoders = {}
        self.feature_names_out = None
        self.selected_features = None
        self.pca_components = None
        
    def analyze_data_types(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Analyze and categorize column types"""
        analysis = {
            'numerical': [],
            'categorical': [],
            'datetime': [],
            'boolean': [],
            'text': []
        }
        
        for col in df.columns:
            dtype = str(df[col].dtype)
            
            if 'datetime' in dtype.lower():
                analysis['datetime'].append(col)
            elif df[col].dtype in ['bool'] or df[col].nunique() == 2:
                analysis['boolean'].append(col)
            elif df[col].dtype in ['object', 'category']:
                # Check if it's actually text data
                avg_length = df[col].astype(str).str.len().mean()
                if avg_length > 50:  # Likely text
                    analysis['text'].append(col)
                else:
                    analysis['categorical'].append(col)
            elif df[col].dtype in ['int64', 'float64']:
                analysis['numerical'].append(col)
        
        return analysis
    
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Intelligently handle missing values based on data type"""
        df_processed = df.copy()
        
        for col in df_processed.columns:
            missing_pct = df_processed[col].isnull().sum() / len(df_processed)
            
            if missing_pct == 0:
                continue
            elif missing_pct > 0.5:
                # Drop columns with >50% missing values
                df_processed = df_processed.drop(columns=[col])
                continue
            
            if df_processed[col].dtype in ['int64', 'float64']:
                # Numerical: use median for skewed data, mean for normal
                if df_processed[col].skew() > 1:
                    df_processed[col] = df_processed[col].fillna(df_processed[col].median())
                else:
                    df_processed[col] = df_processed[col].fillna(df_processed[col].mean())
            else:
                # Categorical: use mode
                mode_value = df_processed[col].mode()
                if not mode_value.empty:
                    df_processed[col] = df_processed[col].fillna(mode_value[0])
                else:
                    df_processed[col] = df_processed[col].fillna('Unknown')
        
        return df_processed
    
    def encode_categorical_features(self, df: pd.DataFrame, categorical_cols: List[str]) -> pd.DataFrame:
        """Encode categorical variables appropriately"""
        df_processed = df.copy()
        
        for col in categorical_cols:
            if col not in df_processed.columns:
                continue
                
            unique_vals = df_processed[col].nunique()
            
            if unique_vals <= 2:
                # Binary: Label encoding
                le = LabelEncoder()
                df_processed[col] = le.fit_transform(df_processed[col].astype(str))
                self.encoders[col] = {'type': 'label', 'encoder': le}
            elif unique_vals <= 10:
                # Low cardinality: One-hot encoding
                ohe = OneHotEncoder(sparse_output=False, drop='first')
                encoded = ohe.fit_transform(df_processed[[col]].astype(str))
                feature_names = [f"{col}_{cat}" for cat in ohe.categories_[0][1:]]  # drop='first'
                encoded_df = pd.DataFrame(encoded, columns=feature_names, index=df_processed.index)
                df_processed = pd.concat([df_processed.drop(columns=[col]), encoded_df], axis=1)
                self.encoders[col] = {'type': 'onehot', 'encoder': ohe, 'features': feature_names}
            else:
                # High cardinality: Frequency encoding
                freq_map = df_processed[col].value_counts(normalize=True).to_dict()
                df_processed[f'{col}_freq'] = df_processed[col].map(freq_map)
                df_processed = df_processed.drop(columns=[col])
                self.encoders[col] = {'type': 'frequency', 'mapping': freq_map}
        
        return df_processed
    
    def create_interaction_features(self, df: pd.DataFrame, numerical_cols: List[str], 
                                  max_interactions: int = 10) -> pd.DataFrame:
        """Create interaction features between numerical variables"""
        df_processed = df.copy()
        created_features = 0
        
        # Create pairwise interactions
        for i in range(len(numerical_cols)):
            if created_features >= max_interactions:
                break
            for j in range(i + 1, len(numerical_cols)):
                if created_features >= max_interactions:
                    break
                    
                col1, col2 = numerical_cols[i], numerical_cols[j]
                
                # Multiplication interaction
                interaction_name = f"{col1}_x_{col2}"
                df_processed[interaction_name] = df_processed[col1] * df_processed[col2]
                created_features += 1
                
                if created_features >= max_interactions:
                    break
                
                # Addition interaction
                addition_name = f"{col1}_plus_{col2}"
                df_processed[addition_name] = df_processed[col1] + df_processed[col2]
                created_features += 1
        
        return df_processed
    
    def create_polynomial_features(self, df: pd.DataFrame, numerical_cols: List[str], 
                                 degree: int = 2) -> pd.DataFrame:
        """Create polynomial features for numerical variables"""
        df_processed = df.copy()
        
        for col in numerical_cols[:3]:  # Limit to top 3 numerical columns
            if degree >= 2:
                df_processed[f"{col}_squared"] = df_processed[col] ** 2
            if degree >= 3:
                df_processed[f"{col}_cubed"] = df_processed[col] ** 3
            # Square root (handle negative values)
            df_processed[f"{col}_sqrt"] = np.sqrt(np.abs(df_processed[col]))
        
        return df_processed
    
    def scale_numerical_features(self, df: pd.DataFrame, numerical_cols: List[str], 
                               method: str = 'standard') -> pd.DataFrame:
        """Scale numerical features"""
        df_processed = df.copy()
        
        if method == 'standard':
            scaler = StandardScaler()
        elif method == 'minmax':
            scaler = MinMaxScaler()
        else:
            scaler = StandardScaler()
        
        scaled_data = scaler.fit_transform(df_processed[numerical_cols])
        df_processed[numerical_cols] = scaled_data
        self.scalers['numerical'] = scaler
        
        return df_processed
    
    def apply_pca(self, df: pd.DataFrame, n_components: Union[int, float] = 0.95) -> pd.DataFrame:
        """Apply PCA for dimensionality reduction"""
        pca = PCA(n_components=n_components, random_state=self.random_state)
        pca_result = pca.fit_transform(df)
        
        # Create feature names for PCA components
        n_comp = pca_result.shape[1]
        pca_columns = [f'PC{i+1}' for i in range(n_comp)]
        df_pca = pd.DataFrame(pca_result, columns=pca_columns, index=df.index)
        
        self.pca_components = {
            'pca': pca,
            'explained_variance_ratio': pca.explained_variance_ratio_,
            'n_components': n_comp
        }
        
        return df_pca
    
    def select_k_best_features(self, X: pd.DataFrame, y: pd.Series, k: int = 10, 
                             task_type: str = 'auto') -> pd.DataFrame:
        """Select K best features based on statistical tests"""
        if task_type == 'auto':
            task_type = 'classification' if y.dtype in ['object', 'category'] or y.nunique() <= 20 else 'regression'
        
        if task_type == 'classification':
            if y.dtype in ['object', 'category']:
                # Convert to numeric labels
                le = LabelEncoder()
                y_numeric = le.fit_transform(y)
                selector = SelectKBest(score_func=f_classif, k=min(k, X.shape[1]))
            else:
                selector = SelectKBest(score_func=f_classif, k=min(k, X.shape[1]))
        else:
            selector = SelectKBest(score_func=f_regression, k=min(k, X.shape[1]))
        
        X_selected = selector.fit_transform(X, y)
        selected_features = X.columns[selector.get_support()].tolist()
        
        self.selected_features = {
            'selected': selected_features,
            'scores': dict(zip(X.columns, selector.scores_)),
            'selector': selector
        }
        
        return pd.DataFrame(X_selected, columns=selected_features, index=X.index)
    
    def engineer_dataframe(self, df: pd.DataFrame, target_column: Optional[str] = None, 
                          feature_strategy: str = 'comprehensive') -> pd.DataFrame:
        """
        Complete automated feature engineering pipeline
        
        Args:
            df: Input DataFrame
            target_column: Name of target variable (will be excluded from transformations)
            feature_strategy: 'minimal', 'balanced', or 'comprehensive'
            
        Returns:
            Processed DataFrame ready for ML
        """
        df_processed = df.copy()
        
        # Analyze data types
        dtypes = self.analyze_data_types(df_processed)
        
        # Handle missing values
        df_processed = self.handle_missing_values(df_processed)
        
        # Separate target if provided
        if target_column and target_column in df_processed.columns:
            y = df_processed[target_column]
            X = df_processed.drop(columns=[target_column])
            dtypes_no_target = self.analyze_data_types(X)
        else:
            X = df_processed
            y = None
            dtypes_no_target = dtypes
        
        # Encode categorical features
        if dtypes_no_target['categorical']:
            X = self.encode_categorical_features(X, dtypes_no_target['categorical'])
        
        # Handle numerical features
        if dtypes_no_target['numerical']:
            numerical_cols = [col for col in dtypes_no_target['numerical'] 
                            if col in X.columns]
            
            if feature_strategy in ['balanced', 'comprehensive']:
                # Create interaction features
                X = self.create_interaction_features(X, numerical_cols)
                
                # Create polynomial features (comprehensive only)
                if feature_strategy == 'comprehensive':
                    X = self.create_polynomial_features(X, numerical_cols)
            
            # Scale numerical features
            final_numerical_cols = [col for col in X.columns 
                                  if X[col].dtype in ['int64', 'float64']]
            if final_numerical_cols:
                X = self.scale_numerical_features(X, final_numerical_cols)
        
        # Feature selection for comprehensive strategy
        if feature_strategy == 'comprehensive' and y is not None and len(X.columns) > 15:
            k = min(15, len(X.columns))
            X = self.select_k_best_features(X, y, k=k)
        
        self.feature_names_out = X.columns.tolist()
        
        return X
    
    def get_feature_engineering_report(self) -> Dict[str, Any]:
        """Generate report of applied transformations"""
        report = {
            'feature_names_out': self.feature_names_out,
            'scalings_applied': len(self.scalers) > 0,
            'encodings_applied': len(self.encoders),
            'pca_applied': self.pca_components is not None,
            'feature_selection_applied': self.selected_features is not None
        }
        
        if self.pca_components:
            report['pca_info'] = {
                'n_components': self.pca_components['n_components'],
                'explained_variance_ratio': self.pca_components['explained_variance_ratio'].tolist()
            }
        
        if self.selected_features:
            report['selected_features'] = self.selected_features['selected']
            report['feature_scores'] = self.selected_features['scores']
        
        return report


class TimeSeriesFeatureEngineer:
    """Specialized feature engineering for time series data"""
    
    def __init__(self):
        pass
    
    def create_time_features(self, df: pd.DataFrame, datetime_column: str) -> pd.DataFrame:
        """Extract time-based features from datetime column"""
        df_processed = df.copy()
        
        if datetime_column not in df_processed.columns:
            return df_processed
            
        dt_series = pd.to_datetime(df_processed[datetime_column])
        
        # Basic time features
        df_processed[f'{datetime_column}_year'] = dt_series.dt.year
        df_processed[f'{datetime_column}_month'] = dt_series.dt.month
        df_processed[f'{datetime_column}_day'] = dt_series.dt.day
        df_processed[f'{datetime_column}_dayofweek'] = dt_series.dt.dayofweek
        df_processed[f'{datetime_column}_quarter'] = dt_series.dt.quarter
        
        # Cyclical encoding for seasonal patterns
        df_processed[f'{datetime_column}_month_sin'] = np.sin(2 * np.pi * dt_series.dt.month / 12)
        df_processed[f'{datetime_column}_month_cos'] = np.cos(2 * np.pi * dt_series.dt.month / 12)
        df_processed[f'{datetime_column}_day_sin'] = np.sin(2 * np.pi * dt_series.dt.dayofweek / 7)
        df_processed[f'{datetime_column}_day_cos'] = np.cos(2 * np.pi * dt_series.dt.dayofweek / 7)
        
        return df_processed
    
    def create_lag_features(self, df: pd.DataFrame, value_column: str, 
                          lags: List[int] = [1, 2, 3, 7]) -> pd.DataFrame:
        """Create lag features for time series forecasting"""
        df_processed = df.copy()
        
        for lag in lags:
            df_processed[f'{value_column}_lag_{lag}'] = df_processed[value_column].shift(lag)
        
        return df_processed
    
    def create_rolling_features(self, df: pd.DataFrame, value_column: str,
                              windows: List[int] = [3, 7, 14]) -> pd.DataFrame:
        """Create rolling statistics features"""
        df_processed = df.copy()
        
        for window in windows:
            df_processed[f'{value_column}_rolling_mean_{window}'] = \
                df_processed[value_column].rolling(window=window).mean()
            df_processed[f'{value_column}_rolling_std_{window}'] = \
                df_processed[value_column].rolling(window=window).std()
            df_processed[f'{value_column}_rolling_min_{window}'] = \
                df_processed[value_column].rolling(window=window).min()
            df_processed[f'{value_column}_rolling_max_{window}'] = \
                df_processed[value_column].rolling(window=window).max()
        
        return df_processed


# 导出主要类
__all__ = ['AutomatedFeatureEngineer', 'TimeSeriesFeatureEngineer']