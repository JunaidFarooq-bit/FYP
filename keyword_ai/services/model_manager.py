"""
ML Model Singleton Manager for WebLift.

Optimizes model loading by maintaining singleton instances
and providing efficient model access patterns.
"""
import logging
import os
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Singleton manager for ML models to optimize loading and memory usage.

    Heavy ML libraries are imported lazily so the web process can boot without
    loading Torch/SentenceTransformers until keyword features actually need them.
    """

    _instance = None
    _lock = threading.Lock()
    _models: Dict[str, Any] = {}
    _device: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the manager without importing heavy ML libraries."""
        self._device = None
        logger.info("ModelManager initialized with lazy ML loading")

    def _get_torch(self):
        import torch

        return torch

    def _get_device(self) -> str:
        """Determine the best available device for model inference."""
        if self._device:
            return self._device

        torch = self._get_torch()
        if torch.cuda.is_available():
            self._device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self._device = "mps"
        else:
            self._device = "cpu"

        logger.info("ModelManager selected device: %s", self._device)
        return self._device

    def get_embedding_model(self, model_name: str = None):
        """Get or load the sentence transformer model."""
        model_name = model_name or os.getenv("KEYWORD_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        cache_key = f"embedding_{model_name}"

        if cache_key not in self._models:
            with self._lock:
                if cache_key not in self._models:
                    from sentence_transformers import SentenceTransformer

                    device = self._get_device()
                    logger.info("Loading embedding model: %s", model_name)
                    try:
                        model = SentenceTransformer(model_name, device=device)

                        if device == "cuda":
                            model.half()
                            model.eval()

                        self._models[cache_key] = model
                        logger.info("Model %s loaded successfully on %s", model_name, device)

                    except Exception as e:
                        logger.error("Failed to load model %s: %s", model_name, e)
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
                    from sentence_transformers import CrossEncoder

                    device = self._get_device()
                    logger.info("Loading keyword reranker: %s", model_name)
                    self._models[cache_key] = CrossEncoder(model_name, device=device)
        return self._models[cache_key]

    def get_model_info(self, model_name: str = None) -> Dict[str, Any]:
        """Get information about a loaded model."""
        model_name = model_name or os.getenv("KEYWORD_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        cache_key = f"embedding_{model_name}"

        if cache_key not in self._models:
            return {"status": "not_loaded"}

        model = self._models[cache_key]
        return {
            "status": "loaded",
            "device": str(model.device),
            "model_name": model_name,
            "max_seq_length": getattr(model, "max_seq_length", "unknown"),
            "embedding_dimension": model.get_sentence_embedding_dimension(),
        }

    def unload_model(self, model_name: str = None):
        """Unload a model to free memory."""
        model_name = model_name or os.getenv("KEYWORD_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        cache_key = f"embedding_{model_name}"

        if cache_key in self._models:
            with self._lock:
                if cache_key in self._models:
                    del self._models[cache_key]
                    logger.info("Model %s unloaded", model_name)

                    if self._device == "cuda":
                        self._get_torch().cuda.empty_cache()

    def clear_all_models(self):
        """Clear all loaded models to free memory."""
        with self._lock:
            self._models.clear()
            if self._device == "cuda":
                self._get_torch().cuda.empty_cache()
            logger.info("All models cleared")

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage information."""
        info = {
            "loaded_models": list(self._models.keys()),
            "device": self._device or "not_selected",
        }

        if self._device == "cuda":
            torch = self._get_torch()
            info.update({
                "gpu_memory_allocated": torch.cuda.memory_allocated(),
                "gpu_memory_reserved": torch.cuda.memory_reserved(),
                "gpu_memory_total": torch.cuda.get_device_properties(0).total_memory,
            })

        return info


model_manager = ModelManager()


def get_embedding_model(model_name: str = None):
    return model_manager.get_embedding_model(model_name)


def get_model_info(model_name: str = None) -> Dict[str, Any]:
    return model_manager.get_model_info(model_name)


def get_reranker_model(model_name: str = None):
    return model_manager.get_reranker_model(model_name)
