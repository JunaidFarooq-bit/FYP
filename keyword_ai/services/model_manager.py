"""
ML Model Singleton Manager for WebLift.

Optimizes model loading by maintaining singleton instances
and providing efficient model access patterns.
"""
import threading
import os
import logging
from typing import Optional, Dict, Any
from sentence_transformers import SentenceTransformer, CrossEncoder
import torch
from django.conf import settings

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Singleton manager for ML models to optimize loading and memory usage.
    
    Features:
    - Thread-safe singleton pattern
    - Lazy loading of models
    - Model caching and reuse
    - Memory optimization
    """
    
    _instance = None
    _lock = threading.Lock()
    _models: Dict[str, Any] = {}
    _device = None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the model manager."""
        self._device = self._get_device()
        logger.info(f"ModelManager initialized on device: {self._device}")
    
    def _get_device(self) -> str:
        """Determine the best available device for model inference."""
        if torch.cuda.is_available():
            return 'cuda'
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return 'mps'  # Apple Silicon
        else:
            return 'cpu'
    
    def get_embedding_model(self, model_name: str = None) -> SentenceTransformer:
        """
        Get or load the sentence transformer model.
        
        Args:
            model_name: Name of the sentence transformer model
            
        Returns:
            SentenceTransformer instance
        """
        model_name = model_name or os.getenv('KEYWORD_EMBEDDING_MODEL', 'BAAI/bge-small-en-v1.5')
        cache_key = f'embedding_{model_name}'
        
        if cache_key not in self._models:
            with self._lock:
                # Double-check pattern
                if cache_key not in self._models:
                    logger.info(f"Loading embedding model: {model_name}")
                    try:
                        model = SentenceTransformer(model_name, device=self._device)
                        
                        # Optimize model for inference
                        if self._device == 'cuda':
                            model.half()  # Use FP16 for GPU
                            model.eval()
                        
                        self._models[cache_key] = model
                        logger.info(f"Model {model_name} loaded successfully on {self._device}")
                        
                    except Exception as e:
                        logger.error(f"Failed to load model {model_name}: {e}")
                        raise
        
        return self._models[cache_key]
    
    def get_reranker_model(self, model_name: str = None):
        """Get the shared local cross-encoder used for candidate reranking."""
        model_name = model_name or os.getenv(
            "KEYWORD_RERANKER_MODEL",
            "cross-encoder/ms-marco-MiniLM-L6-v2",
        )
        cache_key = f"reranker_{model_name}"
        if cache_key not in self._models:
            with self._lock:
                if cache_key not in self._models:
                    logger.info("Loading keyword reranker: %s", model_name)
                    self._models[cache_key] = CrossEncoder(model_name, device=self._device)
        return self._models[cache_key]


    def get_model_info(self, model_name: str = None) -> Dict[str, Any]:
        """
        Get information about a loaded model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Dictionary with model information
        """
        model_name = model_name or os.getenv('KEYWORD_EMBEDDING_MODEL', 'BAAI/bge-small-en-v1.5')
        cache_key = f'embedding_{model_name}'
        
        if cache_key not in self._models:
            return {'status': 'not_loaded'}
        
        model = self._models[cache_key]
        return {
            'status': 'loaded',
            'device': str(model.device),
            'model_name': model_name,
            'max_seq_length': getattr(model, 'max_seq_length', 'unknown'),
            'embedding_dimension': model.get_sentence_embedding_dimension(),
        }
    
    def unload_model(self, model_name: str = None):
        """
        Unload a model to free memory.
        
        Args:
            model_name: Name of the model to unload
        """
        model_name = model_name or os.getenv('KEYWORD_EMBEDDING_MODEL', 'BAAI/bge-small-en-v1.5')
        cache_key = f'embedding_{model_name}'
        
        if cache_key in self._models:
            with self._lock:
                if cache_key in self._models:
                    del self._models[cache_key]
                    logger.info(f"Model {model_name} unloaded")
                    
                    # Clear GPU cache if using CUDA
                    if self._device == 'cuda':
                        torch.cuda.empty_cache()
    
    def clear_all_models(self):
        """Clear all loaded models to free memory."""
        with self._lock:
            self._models.clear()
            if self._device == 'cuda':
                torch.cuda.empty_cache()
            logger.info("All models cleared")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage information."""
        info = {
            'loaded_models': list(self._models.keys()),
            'device': self._device,
        }
        
        if self._device == 'cuda':
            info.update({
                'gpu_memory_allocated': torch.cuda.memory_allocated(),
                'gpu_memory_reserved': torch.cuda.memory_reserved(),
                'gpu_memory_total': torch.cuda.get_device_properties(0).total_memory,
            })
        
        return info


# Global instance for easy access
model_manager = ModelManager()


def get_embedding_model(model_name: str = None) -> SentenceTransformer:
    """
    Convenience function to get the embedding model.
    
    Args:
        model_name: Name of the sentence transformer model
        
    Returns:
        SentenceTransformer instance
    """
    return model_manager.get_embedding_model(model_name)


def get_model_info(model_name: str = None) -> Dict[str, Any]:
    """
    Convenience function to get model information.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Dictionary with model information
    """
    return model_manager.get_model_info(model_name)


def get_reranker_model(model_name: str = None):
    return model_manager.get_reranker_model(model_name)
