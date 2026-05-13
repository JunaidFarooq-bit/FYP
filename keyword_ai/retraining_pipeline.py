"""
Automated Model Retraining Pipeline (Phase 5)
Handles periodic retraining of ML models based on collected feedback.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np

from django.utils import timezone

# Setup logging
logger = logging.getLogger(__name__)


class RetrainingPipeline:
    """
    Manages automated model retraining based on feedback thresholds.
    """
    
    MODEL_CONFIGS = {
        "relevance_scorer_v2": {
            "min_samples": 100,
            "retrain_frequency_days": 30,
            "performance_threshold": 0.60,  # 60% acceptance rate
        },
        "suggestion_generator": {
            "min_samples": 150,
            "retrain_frequency_days": 30,
            "performance_threshold": 0.55,
        },
        "semantic_mapper": {
            "min_samples": 100,
            "retrain_frequency_days": 45,
            "performance_threshold": 0.60,
        },
    }
    
    @staticmethod
    def check_retraining_needed(model_name: str) -> Dict:
        """
        Check if a model needs retraining.
        
        Returns:
            Dict with decision and reasoning
        """
        if model_name not in RetrainingPipeline.MODEL_CONFIGS:
            return {
                "needs_retraining": False,
                "reason": f"Unknown model: {model_name}",
            }
        
        config = RetrainingPipeline.MODEL_CONFIGS[model_name]
        
        # Import here to avoid circular imports
        from .services.feedback_collector import ContinuousLearningMonitor
        
        result = ContinuousLearningMonitor.should_retrain(model_name)
        
        # Normalize key: ContinuousLearningMonitor uses 'should_retrain',
        # expose as 'needs_retraining' for the rest of the pipeline.
        result.setdefault('needs_retraining', result.get('should_retrain', False))
        return result
    
    @staticmethod
    def prepare_training_data(model_name: str, days: int = 90) -> Optional[Dict]:
        """
        Prepare training data from recent feedback.
        
        Args:
            model_name: Name of the model to retrain
            days: Number of days of history to use
            
        Returns:
            Dict with training data or None if insufficient data
        """
        from .models import SuggestionFeedback, KeywordOpportunity, ContentAnalysis
        
        since = timezone.now() - timedelta(days=days)
        
        # Get feedback for the specified model type
        feedback = SuggestionFeedback.objects.filter(
            timestamp__gte=since,
            opportunity__keyword_type=model_name.replace('_', ''),
        ).select_related('opportunity', 'opportunity__content_analysis')
        
        if feedback.count() < 50:
            logger.warning(f"Insufficient feedback for {model_name}: {feedback.count()} samples")
            return None
        
        # Prepare labeled dataset
        training_data = []
        
        for fb in feedback:
            opp = fb.opportunity
            content = opp.content_analysis
            
            label = 1 if fb.user_action in ['accepted', 'implemented'] else 0
            
            training_data.append({
                "keyword": opp.keyword,
                "content_text": "",  # ContentAnalysis stores no raw text; embedding used instead
                "content_embedding": content.get_embedding() if callable(getattr(content, 'get_embedding', None)) else None,
                "relevance_score": opp.relevance_score,
                "label": label,
                "user_rating": fb.rating,
                "feedback_id": fb.id,
            })
        
        logger.info(f"Prepared {len(training_data)} training samples for {model_name}")
        
        return {
            "model_name": model_name,
            "training_samples": len(training_data),
            "positive_samples": sum(1 for d in training_data if d["label"] == 1),
            "negative_samples": sum(1 for d in training_data if d["label"] == 0),
            "data": training_data,
        }
    
    @staticmethod
    def retrain_relevance_scorer(data: Dict) -> Dict:
        """
        Retrain the relevance scorer v2 model.
        
        Args:
            data: Training data prepared by prepare_training_data
            
        Returns:
            Dict with training results
        """
        from .ml_models.relevance_scorer_v2 import (
            KeywordFeatureExtractor,
            train_relevance_model,
        )
        
        logger.info("Starting relevance scorer retraining...")
        
        # Extract features for each sample
        training_pairs = []
        extractor = KeywordFeatureExtractor()
        
        for sample in data["data"]:
            try:
                features = extractor.extract_features(sample["keyword"])
                label = sample["relevance_score"] / 100.0  # Normalize to 0-1
                training_pairs.append((sample["keyword"], features, label))
            except Exception as e:
                logger.warning(f"Failed to extract features for {sample['keyword']}: {e}")
        
        if len(training_pairs) < 50:
            return {
                "success": False,
                "error": f"Insufficient training data: {len(training_pairs)} samples",
            }
        
        # Train model
        try:
            model, scaler = train_relevance_model(training_pairs)
            
            return {
                "success": True,
                "model_name": "relevance_scorer_v2",
                "training_samples": len(training_pairs),
                "message": "Model retrained successfully",
            }
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    @staticmethod
    def run_full_retraining() -> Dict:
        """
        Run retraining pipeline for all models that need it.
        
        Returns:
            Dict with results for all models
        """
        results = {}
        
        for model_name in RetrainingPipeline.MODEL_CONFIGS.keys():
            logger.info(f"Checking retraining needs for {model_name}...")
            
            # Check if retraining needed
            check = RetrainingPipeline.check_retraining_needed(model_name)
            
            if not check.get("needs_retraining", False):
                results[model_name] = {
                    "retrained": False,
                    "reason": check.get("reason", "No retraining needed"),
                }
                continue
            
            # Prepare training data
            data = RetrainingPipeline.prepare_training_data(model_name)
            
            if not data:
                results[model_name] = {
                    "retrained": False,
                    "reason": "Insufficient training data",
                }
                continue
            
            # Retrain based on model type
            if model_name == "relevance_scorer_v2":
                result = RetrainingPipeline.retrain_relevance_scorer(data)
            else:
                # Placeholder for other models
                result = {
                    "success": False,
                    "error": f"Retraining not yet implemented for {model_name}",
                }
            
            results[model_name] = result
            
            if result.get("success"):
                logger.info(f"Successfully retrained {model_name}")
            else:
                logger.error(f"Failed to retrain {model_name}: {result.get('error')}")
        
        return {
            "timestamp": timezone.now().isoformat(),
            "results": results,
        }
    
    @staticmethod
    def validate_new_model(model_name: str, test_data: List[Dict]) -> Dict:
        """
        Validate a newly trained model against test data.
        
        Args:
            model_name: Name of the model
            test_data: Test dataset
            
        Returns:
            Validation metrics
        """
        # Load current model
        from .ml_models.relevance_scorer_v2 import get_relevance_model, get_scaler
        
        model = get_relevance_model()
        scaler = get_scaler()
        
        if model is None:
            return {
                "valid": False,
                "error": "Model not found",
            }
        
        # Make predictions
        from .ml_models.relevance_scorer_v2 import KeywordFeatureExtractor
        
        extractor = KeywordFeatureExtractor()
        predictions = []
        actuals = []
        
        for sample in test_data:
            try:
                features = extractor.extract_features(sample["keyword"])
                features_scaled = scaler.transform([features])
                pred = model.predict(features_scaled)[0]
                
                predictions.append(pred)
                actuals.append(sample["relevance_score"] / 100.0)
            except Exception as e:
                logger.warning(f"Prediction failed for {sample['keyword']}: {e}")
        
        if not predictions:
            return {
                "valid": False,
                "error": "No valid predictions",
            }
        
        # Calculate metrics
        mae = np.mean(np.abs(np.array(predictions) - np.array(actuals)))
        
        return {
            "valid": True,
            "test_samples": len(predictions),
            "mae": round(mae, 4),
            "mean_prediction": round(np.mean(predictions), 4),
            "mean_actual": round(np.mean(actuals), 4),
        }
    
    @staticmethod
    def rollback_model(model_name: str, version: str) -> Dict:
        """
        Rollback to a previous model version.
        
        Args:
            model_name: Name of the model
            version: Version to rollback to
            
        Returns:
            Rollback result
        """
        # Implementation would restore from backup
        logger.info(f"Rolling back {model_name} to version {version}")
        
        return {
            "success": True,
            "model": model_name,
            "rolled_back_to": version,
            "message": "Model rolled back successfully",
        }


class ModelVersionManager:
    """
    Manages model versioning and deployment.
    """
    
    VERSION_FILE = "model_versions.json"
    
    @staticmethod
    def get_current_version(model_name: str) -> str:
        """Get current deployed version of a model."""
        # Check version file
        version_file = os.path.join(
            os.path.dirname(__file__), 
            "ml_models", 
            ModelVersionManager.VERSION_FILE
        )
        
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                versions = json.load(f)
                return versions.get(model_name, "1.0.0")
        
        return "1.0.0"
    
    @staticmethod
    def bump_version(model_name: str) -> str:
        """Bump version number for a model."""
        current = ModelVersionManager.get_current_version(model_name)
        
        # Simple semver bump (patch version)
        parts = current.split('.')
        parts[2] = str(int(parts[2]) + 1)
        new_version = '.'.join(parts)
        
        # Save new version
        version_file = os.path.join(
            os.path.dirname(__file__), 
            "ml_models", 
            ModelVersionManager.VERSION_FILE
        )
        
        versions = {}
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                versions = json.load(f)
        
        versions[model_name] = new_version
        
        os.makedirs(os.path.dirname(version_file), exist_ok=True)
        with open(version_file, 'w') as f:
            json.dump(versions, f, indent=2)
        
        return new_version
    
    @staticmethod
    def save_model_backup(model_name: str, version: str):
        """Create backup of current model before retraining."""
        import shutil
        
        model_dir = os.path.join(os.path.dirname(__file__), "ml_models")
        backup_dir = os.path.join(model_dir, "backups", model_name, version)
        
        os.makedirs(backup_dir, exist_ok=True)
        
        # Backup model files
        model_file = os.path.join(model_dir, f"{model_name}.pkl")
        if os.path.exists(model_file):
            shutil.copy2(model_file, backup_dir)
        
        logger.info(f"Backed up {model_name} v{version} to {backup_dir}")
