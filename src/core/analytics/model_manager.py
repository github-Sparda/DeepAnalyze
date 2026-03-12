"""
Model Management System for DeepAnalyze
Handles model persistence, versioning, performance tracking, and deployment
"""

from __future__ import annotations

import json
import pickle
import hashlib
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from datetime import datetime
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.model_selection import cross_val_score


class ModelManager:
    """
    Comprehensive model management system that handles:
    - Model persistence and loading
    - Version control
    - Performance tracking
    - Model comparison
    - Deployment utilities
    """
    
    def __init__(self, models_dir: Union[str, Path] = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.registry_file = self.models_dir / "model_registry.json"
        self.load_registry()
    
    def load_registry(self):
        """Load model registry from file"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                self.registry = json.load(f)
        else:
            self.registry = {}
    
    def save_registry(self):
        """Save model registry to file"""
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2, default=str)
    
    def generate_model_hash(self, model: BaseEstimator, X_sample: pd.DataFrame = None) -> str:
        """Generate unique hash for model based on parameters and sample data"""
        model_str = str(model.get_params())
        if X_sample is not None:
            model_str += str(X_sample.shape)
            model_str += str(X_sample.dtypes.to_dict())
        return hashlib.md5(model_str.encode()).hexdigest()[:12]
    
    def save_model(self, model: BaseEstimator, model_name: str, 
                   X_sample: pd.DataFrame = None, metadata: Dict[str, Any] = None) -> str:
        """
        Save trained model with metadata
        
        Args:
            model: Trained sklearn model
            model_name: Name to identify the model
            X_sample: Sample data for generating unique identifier
            metadata: Additional metadata dictionary
            
        Returns:
            Model ID (hash)
        """
        # Generate unique model ID
        model_id = self.generate_model_hash(model, X_sample)
        
        # Create model directory
        model_dir = self.models_dir / model_id
        model_dir.mkdir(exist_ok=True)
        
        # Save model
        model_path = model_dir / "model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        # Save metadata
        model_metadata = {
            'model_id': model_id,
            'model_name': model_name,
            'model_type': model.__class__.__name__,
            'parameters': model.get_params(),
            'created_at': datetime.now().isoformat(),
            'saved_at': datetime.now().isoformat(),
            'performance': {},
            'metadata': metadata or {}
        }
        
        # Add sample data info if provided
        if X_sample is not None:
            model_metadata['sample_shape'] = X_sample.shape
            model_metadata['sample_columns'] = X_sample.columns.tolist()
        
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(model_metadata, f, indent=2, default=str)
        
        # Update registry
        if model_id not in self.registry:
            self.registry[model_id] = []
        
        self.registry[model_id].append(model_metadata)
        self.save_registry()
        
        return model_id
    
    def load_model(self, model_id: str, version: int = -1) -> tuple[BaseEstimator, Dict[str, Any]]:
        """
        Load model and metadata
        
        Args:
            model_id: Model identifier
            version: Version index (-1 for latest)
            
        Returns:
            Tuple of (model, metadata)
        """
        model_dir = self.models_dir / model_id
        if not model_dir.exists():
            raise FileNotFoundError(f"Model {model_id} not found")
        
        versions = self.registry.get(model_id, [])
        if not versions:
            raise ValueError(f"No versions found for model {model_id}")
        
        # Get specified version
        version_idx = version if version >= 0 else len(versions) + version
        if version_idx < 0 or version_idx >= len(versions):
            raise ValueError(f"Version {version} not found for model {model_id}")
        
        version_metadata = versions[version_idx]
        
        # Load model
        model_path = model_dir / "model.pkl"
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        return model, version_metadata
    
    def evaluate_model(self, model: BaseEstimator, X: pd.DataFrame, y: pd.Series, 
                      cv: int = 5, scoring: str = 'auto') -> Dict[str, float]:
        """
        Evaluate model performance with cross-validation
        
        Args:
            model: Trained model
            X: Feature data
            y: Target data
            cv: Number of cross-validation folds
            scoring: Scoring metric ('auto' detects based on model type)
            
        Returns:
            Dictionary of performance metrics
        """
        if scoring == 'auto':
            # Auto-detect scoring based on model type
            if hasattr(model, 'predict_proba'):
                scoring = 'roc_auc'
            elif hasattr(model, 'predict') and len(y.unique()) > 10:
                scoring = 'r2'
            else:
                scoring = 'accuracy'
        
        # Perform cross-validation
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring=scoring)
        
        # Calculate additional metrics
        model.fit(X, y)  # Fit on full data for additional metrics
        y_pred = model.predict(X)
        
        results = {
            'cv_mean': float(cv_scores.mean()),
            'cv_std': float(cv_scores.std()),
            'cv_scores': cv_scores.tolist(),
            'scoring_metric': scoring
        }
        
        # Add task-specific metrics
        if hasattr(model, 'predict_proba'):
            from sklearn.metrics import roc_auc_score, log_loss
            try:
                y_prob = model.predict_proba(X)
                results['roc_auc'] = float(roc_auc_score(y, y_prob[:, 1]))
                results['log_loss'] = float(log_loss(y, y_prob))
            except Exception:
                pass
        elif len(y.unique()) > 10:  # Regression
            from sklearn.metrics import mean_squared_error, mean_absolute_error
            mse = float(mean_squared_error(y, y_pred))
            results['mse'] = mse
            results['rmse'] = float(mse ** 0.5)
            results['mae'] = float(mean_absolute_error(y, y_pred))
        else:  # Classification
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
            results['accuracy'] = float(accuracy_score(y, y_pred))
            try:
                results['precision'] = float(precision_score(y, y_pred, average='weighted'))
                results['recall'] = float(recall_score(y, y_pred, average='weighted'))
                results['f1'] = float(f1_score(y, y_pred, average='weighted'))
            except Exception:
                pass
        
        return results
    
    def update_model_performance(self, model_id: str, performance: Dict[str, Any], 
                               version: int = -1):
        """Update performance metrics for a model version"""
        versions = self.registry.get(model_id, [])
        if not versions:
            return
            
        version_idx = version if version >= 0 else len(versions) + version
        if 0 <= version_idx < len(versions):
            versions[version_idx]['performance'].update(performance)
            versions[version_idx]['updated_at'] = datetime.now().isoformat()
            self.save_registry()
    
    def compare_models(self, model_ids: List[str]) -> pd.DataFrame:
        """
        Compare multiple models based on their performance
        
        Args:
            model_ids: List of model identifiers to compare
            
        Returns:
            DataFrame with comparison results
        """
        comparison_data = []
        
        for model_id in model_ids:
            versions = self.registry.get(model_id, [])
            if not versions:
                continue
                
            latest_version = versions[-1]  # Get latest version
            performance = latest_version.get('performance', {})
            
            row = {
                'model_id': model_id,
                'model_name': latest_version.get('model_name', ''),
                'model_type': latest_version.get('model_type', ''),
                'created_at': latest_version.get('created_at', ''),
            }
            
            # Add performance metrics
            row.update(performance)
            comparison_data.append(row)
        
        return pd.DataFrame(comparison_data)
    
    def get_best_model(self, metric: str = 'cv_mean', 
                      model_type: Optional[str] = None) -> Optional[tuple[str, Dict[str, Any]]]:
        """
        Get the best performing model based on specified metric
        
        Args:
            metric: Performance metric to compare
            model_type: Filter by model type (optional)
            
        Returns:
            Tuple of (model_id, metadata) for best model
        """
        best_model = None
        best_score = float('-inf') if 'mean' in metric or metric in ['r2', 'accuracy'] else float('inf')
        
        for model_id, versions in self.registry.items():
            if not versions:
                continue
                
            latest_version = versions[-1]
            
            # Filter by model type if specified
            if model_type and latest_version.get('model_type') != model_type:
                continue
            
            performance = latest_version.get('performance', {})
            if metric in performance:
                score = performance[metric]
                # Handle minimization metrics (lower is better)
                if ('std' in metric or metric in ['mse', 'mae', 'log_loss']) and score < best_score:
                    best_score = score
                    best_model = (model_id, latest_version)
                elif ('mean' in metric or metric in ['r2', 'accuracy', 'f1', 'roc_auc']) and score > best_score:
                    best_score = score
                    best_model = (model_id, latest_version)
        
        return best_model
    
    def list_models(self, model_name: Optional[str] = None, 
                   model_type: Optional[str] = None) -> pd.DataFrame:
        """
        List all registered models with filtering options
        
        Args:
            model_name: Filter by model name (partial match)
            model_type: Filter by model type
            
        Returns:
            DataFrame with model information
        """
        model_list = []
        
        for model_id, versions in self.registry.items():
            if not versions:
                continue
                
            latest_version = versions[-1]  # Get latest version
            
            # Apply filters
            if model_name and model_name.lower() not in latest_version.get('model_name', '').lower():
                continue
            if model_type and latest_version.get('model_type') != model_type:
                continue
            
            model_info = {
                'model_id': model_id,
                'model_name': latest_version.get('model_name', ''),
                'model_type': latest_version.get('model_type', ''),
                'versions': len(versions),
                'created_at': latest_version.get('created_at', ''),
                'last_updated': latest_version.get('updated_at', latest_version.get('created_at', '')),
            }
            
            # Add latest performance metrics
            performance = latest_version.get('performance', {})
            model_info.update({k: v for k, v in performance.items() if isinstance(v, (int, float))})
            
            model_list.append(model_info)
        
        return pd.DataFrame(model_list)
    
    def delete_model(self, model_id: str) -> bool:
        """
        Delete a model and all its versions
        
        Args:
            model_id: Model identifier to delete
            
        Returns:
            True if successful, False otherwise
        """
        if model_id not in self.registry:
            return False
        
        # Remove from registry
        del self.registry[model_id]
        self.save_registry()
        
        # Remove model files
        model_dir = self.models_dir / model_id
        if model_dir.exists():
            import shutil
            shutil.rmtree(model_dir)
        
        return True
    
    def export_model(self, model_id: str, export_path: Union[str, Path], 
                    version: int = -1) -> str:
        """
        Export model as a standalone package
        
        Args:
            model_id: Model identifier
            export_path: Path to export directory
            version: Version to export
            
        Returns:
            Path to exported model package
        """
        export_path = Path(export_path)
        export_path.mkdir(exist_ok=True)
        
        # Load model and metadata
        model, metadata = self.load_model(model_id, version)
        
        # Save model
        model_file = export_path / "model.pkl"
        with open(model_file, 'wb') as f:
            pickle.dump(model, f)
        
        # Save metadata
        metadata_file = export_path / "model_info.json"
        export_metadata = {
            'model_id': model_id,
            'model_name': metadata.get('model_name', ''),
            'model_type': metadata.get('model_type', ''),
            'parameters': metadata.get('parameters', {}),
            'exported_at': datetime.now().isoformat(),
            'required_packages': ['scikit-learn', 'pandas', 'numpy']
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(export_metadata, f, indent=2)
        
        # Create loading script
        loader_script = export_path / "load_model.py"
        loader_content = '''
import pickle
import json
from sklearn.base import BaseEstimator

def load_model():
    """Load the exported model"""
    with open('model.pkl', 'rb') as f:
        model = pickle.load(f)
    return model

def get_model_info():
    """Get model information"""
    with open('model_info.json', 'r') as f:
        return json.load(f)

if __name__ == "__main__":
    model = load_model()
    info = get_model_info()
    print(f"Loaded {info['model_name']} ({info['model_type']})")
'''
        
        with open(loader_script, 'w') as f:
            f.write(loader_content)
        
        return str(export_path)


class ModelDeploymentHelper:
    """Helper utilities for model deployment"""
    
    @staticmethod
    def create_prediction_api(model: BaseEstimator, feature_names: List[str]) -> str:
        """Generate Flask API code for model deployment"""
        api_code = f'''
from flask import Flask, request, jsonify
import pickle
import pandas as pd
import numpy as np

app = Flask(__name__)

# Load model
with open('model.pkl', 'rb') as f:
    model = pickle.load(f)

feature_names = {feature_names}

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Get input data
        data = request.get_json()
        
        # Convert to DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data, columns=feature_names)
        else:
            df = pd.DataFrame([data], columns=feature_names)
        
        # Make predictions
        predictions = model.predict(df)
        
        # Handle probability predictions
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(df).tolist()
            return jsonify({{
                'predictions': predictions.tolist(),
                'probabilities': probabilities
            }})
        else:
            return jsonify({{
                'predictions': predictions.tolist()
            }})
            
    except Exception as e:
        return jsonify({{'error': str(e)}}, 400)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
'''
        return api_code
    
    @staticmethod
    def create_model_card(model_info: Dict[str, Any], performance: Dict[str, Any]) -> str:
        """Generate model documentation card"""
        card = f"""
# Model Card: {model_info.get('model_name', 'Unnamed Model')}

## Model Details
- **Model Type**: {model_info.get('model_type', 'Unknown')}
- **Created**: {model_info.get('created_at', 'Unknown')}
- **Model ID**: {model_info.get('model_id', 'Unknown')}

## Performance Metrics
"""
        
        for metric, value in performance.items():
            if isinstance(value, (int, float)):
                card += f"- **{metric}**: {value:.4f}\n"
        
        card += f"""
## Usage
```python
import pickle

# Load model
with open('model.pkl', 'rb') as f:
    model = pickle.load(f)

# Make predictions
predictions = model.predict(X_new)
```

## Notes
- This model was automatically generated by DeepAnalyze
- Performance metrics based on cross-validation
- Feature engineering was applied automatically
"""
        
        return card


# 导出主要类
__all__ = ['ModelManager', 'ModelDeploymentHelper']
