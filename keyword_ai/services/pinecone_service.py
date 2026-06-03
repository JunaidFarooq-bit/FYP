"""
Pinecone Vector Database Service for Keyword AI

Provides an alternative to pgvector for storing and searching vector embeddings.
Pinecone is a managed vector database optimized for semantic search at scale.

Usage:
    from keyword_ai.services.pinecone_service import PineconeService
    
    # Initialize
    pc = PineconeService()
    
    # Upsert vectors
    pc.upsert_vectors([
        {"id": "analysis_1", "values": [0.1, 0.2, ...], "metadata": {...}},
    ])
    
    # Search
    results = pc.search(query_vector=[0.1, 0.2, ...], top_k=5)
"""

import logging
from typing import List, Dict, Optional, Any
from django.conf import settings
from django.db import connection
from django.core.cache import cache
import numpy as np

from .model_manager import get_embedding_model

logger = logging.getLogger(__name__)

# Pinecone import - will be None if not installed
try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    Pinecone = None
    ServerlessSpec = None
    PINECONE_AVAILABLE = False
    logger.warning("pinecone package not installed. Run: pip install pinecone")


class PineconeService:
    """
    Service class for Pinecone vector database operations.
    
    Handles index management, vector upserts, and similarity search.
    Falls back gracefully if Pinecone is not configured.
    """
    
    def __init__(self):
        """Initialize Pinecone client with settings from Django config."""
        self.client = None
        self.index = None
        self._initialized = False
        
        if not PINECONE_AVAILABLE:
            logger.warning("Pinecone package not available")
            return
            
        if not settings.USE_PINECONE:
            logger.debug("Pinecone disabled (USE_PINECONE=False)")
            return
            
        if not settings.PINECONE_API_KEY:
            logger.warning("Pinecone API key not configured")
            return
        
        try:
            self.client = Pinecone(api_key=settings.PINECONE_API_KEY)
            self.index_name = settings.PINECONE_INDEX_NAME
            self.dimensions = settings.PINECONE_DIMENSIONS
            self.metric = settings.PINECONE_METRIC
            self._initialized = True
            logger.info(f"Pinecone client initialized for index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
    
    def is_ready(self) -> bool:
        """Check if Pinecone is properly configured and ready."""
        return self._initialized and self.client is not None
    
    def create_index(self, force: bool = False) -> bool:
        """
        Create the Pinecone index if it doesn't exist.
        
        Args:
            force: If True, delete existing index and recreate
            
        Returns:
            True if index exists or was created successfully
        """
        if not self.is_ready():
            logger.error("Pinecone not initialized")
            return False
        
        try:
            # Check if index already exists
            existing_indexes = self.client.list_indexes()
            index_names = [idx.name for idx in existing_indexes.indexes] if hasattr(existing_indexes, 'indexes') else []
            
            if self.index_name in index_names:
                if force:
                    logger.info(f"Deleting existing index: {self.index_name}")
                    self.client.delete_index(self.index_name)
                else:
                    logger.info(f"Index {self.index_name} already exists")
                    self.index = self.client.Index(self.index_name)
                    return True
            
            # Create new index
            logger.info(f"Creating Pinecone index: {self.index_name}")
            self.client.create_index(
                name=self.index_name,
                dimension=self.dimensions,
                metric=self.metric,
                spec=ServerlessSpec(
                    cloud=settings.PINECONE_CLOUD,
                    region=settings.PINECONE_REGION
                )
            )
            
            # Get index reference
            self.index = self.client.Index(self.index_name)
            logger.info(f"Index {self.index_name} created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create Pinecone index: {e}")
            return False
    
    def get_index(self):
        """Get or create index reference."""
        if not self.is_ready():
            return None
            
        if self.index is None:
            try:
                self.index = self.client.Index(self.index_name)
            except Exception as e:
                logger.error(f"Failed to get index reference: {e}")
                return None
        
        return self.index
    
    def upsert_vectors(
        self, 
        vectors: List[Dict[str, Any]], 
        namespace: str = ""
    ) -> bool:
        """
        Upsert (insert or update) vectors into Pinecone.
        
        Args:
            vectors: List of vectors with keys: id, values, metadata
                     Example: [{"id": "1", "values": [0.1, ...], "metadata": {...}}]
            namespace: Optional namespace for partitioning data
            
        Returns:
            True if successful
        """
        if not self.is_ready():
            logger.error("Pinecone not initialized")
            return False
        
        index = self.get_index()
        if not index:
            return False
        
        try:
            # Format vectors for Pinecone
            formatted_vectors = []
            for v in vectors:
                vec = {
                    "id": str(v["id"]),
                    "values": v["values"] if isinstance(v["values"], list) else v["values"].tolist(),
                }
                if "metadata" in v and v["metadata"]:
                    vec["metadata"] = v["metadata"]
                formatted_vectors.append(vec)
            
            # Batch upsert (Pinecone recommends batches of 100-200)
            batch_size = 100
            for i in range(0, len(formatted_vectors), batch_size):
                batch = formatted_vectors[i:i + batch_size]
                index.upsert(vectors=batch, namespace=namespace)
            
            logger.info(f"Upserted {len(vectors)} vectors to Pinecone")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            return False
    
    def search(
        self, 
        query_vector: List[float], 
        top_k: int = 5,
        namespace: str = "",
        filter_dict: Optional[Dict] = None,
        min_quality_score: Optional[float] = None
    ) -> List[Dict]:
        """
        Search for similar vectors in Pinecone.
        
        Args:
            query_vector: The embedding vector to search for (384-dim)
            top_k: Number of results to return
            namespace: Optional namespace to search within
            filter_dict: Optional metadata filters
            min_quality_score: Filter by minimum quality score (maps to metadata filter)
            
        Returns:
            List of similar vectors with metadata
        """
        if not self.is_ready():
            logger.error("Pinecone not initialized")
            return []
        
        index = self.get_index()
        if not index:
            return []
        
        try:
            # Build filter
            pc_filter = filter_dict or {}
            if min_quality_score is not None:
                pc_filter["quality_score"] = {"$gte": min_quality_score}
            
            # Convert numpy array to list if needed
            if isinstance(query_vector, np.ndarray):
                query_vector = query_vector.tolist()
            
            # Query Pinecone
            results = index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter=pc_filter if pc_filter else None,
                include_metadata=True
            )
            
            # Format results
            formatted_results = []
            for match in results.matches:
                result = {
                    "id": match.id,
                    "score": match.score,
                    "similarity": match.score,  # Pinecone returns similarity directly
                }
                if match.metadata:
                    result.update({
                        "url": match.metadata.get("url"),
                        "title": match.metadata.get("title"),
                        "quality_score": match.metadata.get("quality_score"),
                        "analyzed_at": match.metadata.get("analyzed_at"),
                    })
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def delete_vectors(self, ids: List[str], namespace: str = "") -> bool:
        """
        Delete vectors by IDs.
        
        Args:
            ids: List of vector IDs to delete
            namespace: Optional namespace
            
        Returns:
            True if successful
        """
        if not self.is_ready():
            return False
        
        index = self.get_index()
        if not index:
            return False
        
        try:
            index.delete(ids=ids, namespace=namespace)
            logger.info(f"Deleted {len(ids)} vectors from Pinecone")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get index statistics."""
        if not self.is_ready():
            return {"error": "Pinecone not initialized"}
        
        index = self.get_index()
        if not index:
            return {"error": "Index not available"}
        
        try:
            stats = index.describe_index_stats()
            return {
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "total_vector_count": stats.total_vector_count,
                "namespaces": stats.namespaces if hasattr(stats, 'namespaces') else {}
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}


# Singleton instance
_pinecone_service = None


def get_pinecone_service() -> PineconeService:
    """Get or create singleton Pinecone service instance."""
    global _pinecone_service
    if _pinecone_service is None:
        _pinecone_service = PineconeService()
    return _pinecone_service


def sync_content_analysis_to_pinecone(analysis_id: Optional[int] = None) -> bool:
    """
    Sync ContentAnalysis records from PostgreSQL to Pinecone.
    
    Args:
        analysis_id: If provided, sync only this specific record.
                     If None, sync all records with embeddings.
    
    Returns:
        True if sync was successful
    """
    from ..models import ContentAnalysis, KeywordOpportunity
    
    pc = get_pinecone_service()
    if not pc.is_ready():
        logger.error("Pinecone not available for sync")
        return False
    
    try:
        # Build query
        query = ContentAnalysis.objects.filter(embedding__isnull=False)
        if analysis_id:
            query = query.filter(id=analysis_id)
        
        analyses = query.select_related().iterator(chunk_size=100)
        
        vectors_batch = []
        total_synced = 0
        
        for analysis in analyses:
            # Get embedding as list
            embedding = analysis.get_embedding_list()
            if not embedding:
                continue
            
            # Get top keywords for metadata
            keywords = KeywordOpportunity.objects.filter(
                content_analysis=analysis,
                is_rejected=False
            ).order_by('-relevance_score')[:5]
            
            # Build metadata
            metadata = {
                "url": analysis.url,
                "title": analysis.title or "",
                "quality_score": float(analysis.quality_score),
                "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else "",
                "top_keywords": [k.keyword for k in keywords],
                "content_hash": analysis.content_hash,
            }
            
            # Add TF-IDF keywords if available
            if analysis.tfidf_keywords:
                metadata["tfidf_keywords"] = analysis.tfidf_keywords[:10]
            
            vectors_batch.append({
                "id": f"analysis_{analysis.id}",
                "values": embedding,
                "metadata": metadata
            })
            
            # Batch upsert every 100 vectors
            if len(vectors_batch) >= 100:
                if pc.upsert_vectors(vectors_batch):
                    total_synced += len(vectors_batch)
                    logger.info(f"Synced {total_synced} vectors so far...")
                vectors_batch = []
        
        # Upsert remaining vectors
        if vectors_batch:
            if pc.upsert_vectors(vectors_batch):
                total_synced += len(vectors_batch)
        
        logger.info(f"Total vectors synced to Pinecone: {total_synced}")
        return True
        
    except Exception as e:
        logger.error(f"Sync to Pinecone failed: {e}")
        return False


def search_similar_with_pinecone(
    content_embedding: np.ndarray,
    top_k: int = 5,
    min_quality_score: float = 50.0
) -> List[Dict]:
    """
    Search for similar content using Pinecone instead of pgvector.
    
    This is a drop-in replacement for rag_retriever.retrieve_similar_analyses()
    when USE_PINECONE=True.
    
    Args:
        content_embedding: The embedding vector (384-dim)
        top_k: Number of results
        min_quality_score: Minimum quality filter
        
    Returns:
        List of similar analyses formatted like pgvector results
    """
    pc = get_pinecone_service()
    if not pc.is_ready():
        logger.warning("Pinecone not available, falling back to pgvector")
        return []
    
    # Search Pinecone
    results = pc.search(
        query_vector=content_embedding,
        top_k=top_k,
        min_quality_score=min_quality_score
    )
    
    # Format to match pgvector output structure
    formatted = []
    for r in results:
        item = {
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "quality_score": r.get("quality_score", 0),
            "similarity_score": r.get("score", 0),
            "analyzed_at": r.get("analyzed_at", ""),
            "pinecone_id": r.get("id"),
        }
        
        # Add keywords from metadata if available
        if "top_keywords" in r:
            item["top_keywords"] = [{"keyword": k, "score": 0} for k in r["top_keywords"]]
        if "tfidf_keywords" in r:
            item["tfidf_keywords"] = r["tfidf_keywords"]
        
        formatted.append(item)
    
    return formatted
