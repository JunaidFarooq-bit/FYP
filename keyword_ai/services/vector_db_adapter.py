"""
Vector Database Adapter - Unified interface for pgvector and Pinecone

This module provides a unified interface for vector operations that can use
either PostgreSQL with pgvector (default) or Pinecone (when configured).

Switching between backends is controlled by USE_PINECONE setting.

Usage:
    from keyword_ai.services.vector_db_adapter import (
        search_similar_analyses,
        upsert_analysis_embedding,
        get_vector_db_stats
    )
    
    # Search works with either backend based on settings
    results = search_similar_analyses(embedding, top_k=5)
"""

import logging
from typing import List, Dict, Optional, Any
from django.conf import settings
from django.db import models, connection
import numpy as np

logger = logging.getLogger(__name__)


def search_similar_analyses(
    content_embedding: np.ndarray,
    top_k: int = 5,
    min_quality_score: float = 50.0,
    include_keywords: bool = True
) -> List[Dict]:
    """
    Search for similar content analyses using the configured vector database.
    
    Automatically uses Pinecone if USE_PINECONE=True, otherwise uses pgvector.
    
    Args:
        content_embedding: The embedding vector (384-dim for all-MiniLM-L6-v2)
        top_k: Number of similar analyses to retrieve
        min_quality_score: Minimum quality score filter (0-100)
        include_keywords: Whether to include keywords from similar content
        
    Returns:
        List of similar analyses with metadata and keywords
    """
    # Use Pinecone if configured and available
    if settings.USE_PINECONE and settings.PINECONE_API_KEY:
        try:
            from .pinecone_service import search_similar_with_pinecone
            results = search_similar_with_pinecone(
                content_embedding=content_embedding,
                top_k=top_k,
                min_quality_score=min_quality_score
            )
            if results:  # Only use if Pinecone returned results
                logger.debug(f"Retrieved {len(results)} results from Pinecone")
                return results
            logger.warning("Pinecone returned no results, falling back to pgvector")
        except Exception as e:
            logger.error(f"Pinecone search failed, falling back to pgvector: {e}")
    
    # Fall back to pgvector (PostgreSQL)
    return _search_with_pgvector(content_embedding, top_k, min_quality_score, include_keywords)


def _search_with_pgvector(
    content_embedding: np.ndarray,
    top_k: int = 5,
    min_quality_score: float = 50.0,
    include_keywords: bool = True
) -> List[Dict]:
    """
    Internal: Search using PostgreSQL with pgvector extension.
    
    This is the default/fallback implementation that uses the existing
    pgvector setup.
    """
    from ..models import ContentAnalysis, KeywordOpportunity
    
    # Check if PostgreSQL is available
    if connection.vendor != 'postgresql':
        logger.debug("pgvector search skipped: requires PostgreSQL")
        return []
    
    if content_embedding is None or len(content_embedding) == 0:
        return []
    
    # Convert to list for Django ORM
    if isinstance(content_embedding, np.ndarray):
        embedding_list = content_embedding.tolist()
    else:
        embedding_list = content_embedding
    
    try:
        # Use pgvector's cosine distance operator (<=>)
        similar_analyses = ContentAnalysis.objects.filter(
            quality_score__gte=min_quality_score,
            embedding__isnull=False
        ).annotate(
            distance=models.Func(
                models.F('embedding'),
                embedding_list,
                function='embedding <=>',
                output_field=models.FloatField()
            )
        ).order_by('distance')[:top_k]
        
        results = []
        for analysis in similar_analyses:
            # Convert cosine distance to similarity: similarity = 1 - distance
            # Clamp to [0, 1] since distance can be up to 2 for opposite vectors
            raw_similarity = max(0.0, 1 - analysis.distance)
            
            result = {
                'url': analysis.url,
                'quality_score': analysis.quality_score,
                'similarity_score': raw_similarity,
                'analyzed_at': analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
                'title': analysis.title,
            }
            
            if include_keywords:
                # Get top keywords from this similar analysis
                keywords = KeywordOpportunity.objects.filter(
                    content_analysis=analysis,
                    is_rejected=False
                ).order_by('-relevance_score')[:10]
                
                result['top_keywords'] = [
                    {
                        'keyword': kw.keyword,
                        'score': kw.relevance_score,
                        'intent': kw.search_intent,
                        'type': kw.keyword_type
                    }
                    for kw in keywords
                ]
                
                # Also include TF-IDF keywords
                if analysis.tfidf_keywords:
                    result['tfidf_keywords'] = analysis.tfidf_keywords[:10]
            
            results.append(result)
        
        return results
        
    except Exception as e:
        logger.error(f"pgvector search failed: {e}")
        return []


def upsert_analysis_embedding(
    analysis_id: int,
    embedding: np.ndarray,
    metadata: Optional[Dict] = None,
    sync_to_pinecone: bool = True
) -> bool:
    """
    Upsert an embedding for a ContentAnalysis record.
    
    Updates the PostgreSQL record and optionally syncs to Pinecone
    if dual-write mode is enabled.
    
    Args:
        analysis_id: The ContentAnalysis ID
        embedding: The vector embedding (384-dim)
        metadata: Additional metadata for Pinecone
        sync_to_pinecone: Whether to also sync to Pinecone
        
    Returns:
        True if successful
    """
    from ..models import ContentAnalysis
    
    try:
        # Update PostgreSQL
        analysis = ContentAnalysis.objects.get(id=analysis_id)
        
        # Convert numpy to list for storage
        if isinstance(embedding, np.ndarray):
            embedding_list = embedding.tolist()
        else:
            embedding_list = list(embedding)
        
        analysis.embedding = embedding_list
        analysis.save(update_fields=['embedding'])
        
        # Optionally sync to Pinecone
        if sync_to_pinecone and settings.USE_PINECONE:
            from .pinecone_service import get_pinecone_service
            pc = get_pinecone_service()
            
            if pc.is_ready():
                # Build metadata
                pc_metadata = metadata or {
                    "url": analysis.url,
                    "title": analysis.title or "",
                    "quality_score": float(analysis.quality_score),
                    "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else "",
                    "content_hash": analysis.content_hash,
                }
                
                pc.upsert_vectors([{
                    "id": f"analysis_{analysis_id}",
                    "values": embedding_list,
                    "metadata": pc_metadata
                }])
                logger.debug(f"Synced analysis {analysis_id} to Pinecone")
        
        return True
        
    except ContentAnalysis.DoesNotExist:
        logger.error(f"ContentAnalysis {analysis_id} not found")
        return False
    except Exception as e:
        logger.error(f"Failed to upsert embedding: {e}")
        return False


def delete_analysis_embedding(analysis_id: int, delete_from_pinecone: bool = True) -> bool:
    """
    Delete an embedding from both PostgreSQL and optionally Pinecone.
    
    Args:
        analysis_id: The ContentAnalysis ID
        delete_from_pinecone: Whether to also delete from Pinecone
        
    Returns:
        True if successful
    """
    from ..models import ContentAnalysis
    
    try:
        # Clear from PostgreSQL
        analysis = ContentAnalysis.objects.get(id=analysis_id)
        analysis.embedding = None
        analysis.save(update_fields=['embedding'])
        
        # Optionally delete from Pinecone
        if delete_from_pinecone and settings.USE_PINECONE:
            from .pinecone_service import get_pinecone_service
            pc = get_pinecone_service()
            
            if pc.is_ready():
                pc.delete_vectors([f"analysis_{analysis_id}"])
        
        return True
        
    except ContentAnalysis.DoesNotExist:
        logger.error(f"ContentAnalysis {analysis_id} not found")
        return False
    except Exception as e:
        logger.error(f"Failed to delete embedding: {e}")
        return False


def get_vector_db_stats() -> Dict[str, Any]:
    """
    Get statistics about the vector database.
    
    Returns information about both pgvector and Pinecone if configured.
    
    Returns:
        Dict with stats for active backends
    """
    stats = {
        "active_backend": "pgvector",
        "pgvector": {},
        "pinecone": None,
    }
    
    # PostgreSQL stats
    from ..models import ContentAnalysis
    try:
        total_analyses = ContentAnalysis.objects.count()
        with_embeddings = ContentAnalysis.objects.filter(embedding__isnull=False).count()
        
        stats["pgvector"] = {
            "total_analyses": total_analyses,
            "with_embeddings": with_embeddings,
            "coverage_percent": round(with_embeddings / total_analyses * 100, 2) if total_analyses > 0 else 0,
            "database": connection.vendor if connection.vendor == 'postgresql' else "sqlite (limited)",
        }
    except Exception as e:
        stats["pgvector"] = {"error": str(e)}
    
    # Pinecone stats
    if settings.USE_PINECONE:
        try:
            from .pinecone_service import get_pinecone_service
            pc = get_pinecone_service()
            
            if pc.is_ready():
                stats["active_backend"] = "pinecone"
                stats["pinecone"] = pc.get_stats()
            else:
                stats["pinecone"] = {"status": "not_initialized"}
        except Exception as e:
            stats["pinecone"] = {"error": str(e)}
    
    return stats


def batch_sync_to_pinecone(
    analysis_ids: Optional[List[int]] = None,
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    Batch sync embeddings from PostgreSQL to Pinecone.
    
    Useful for initial migration or keeping Pinecone in sync.
    
    Args:
        analysis_ids: Specific IDs to sync, or None for all with embeddings
        batch_size: Number of records per batch
        
    Returns:
        Dict with sync results
    """
    from ..models import ContentAnalysis
    from .pinecone_service import get_pinecone_service
    
    pc = get_pinecone_service()
    if not pc.is_ready():
        return {"success": False, "error": "Pinecone not initialized"}
    
    try:
        # Build query
        query = ContentAnalysis.objects.filter(embedding__isnull=False)
        if analysis_ids:
            query = query.filter(id__in=analysis_ids)
        
        total_to_sync = query.count()
        
        if total_to_sync == 0:
            return {"success": True, "synced": 0, "message": "No records to sync"}
        
        # Process in batches
        synced = 0
        failed = 0
        
        for offset in range(0, total_to_sync, batch_size):
            batch = query[offset:offset + batch_size]
            
            vectors = []
            for analysis in batch:
                try:
                    embedding = analysis.get_embedding_list()
                    if not embedding:
                        continue
                    
                    metadata = {
                        "url": analysis.url,
                        "title": analysis.title or "",
                        "quality_score": float(analysis.quality_score),
                        "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else "",
                        "content_hash": analysis.content_hash,
                    }
                    
                    vectors.append({
                        "id": f"analysis_{analysis.id}",
                        "values": embedding,
                        "metadata": metadata
                    })
                except Exception as e:
                    logger.warning(f"Failed to prepare analysis {analysis.id}: {e}")
                    failed += 1
            
            if vectors:
                if pc.upsert_vectors(vectors):
                    synced += len(vectors)
                else:
                    failed += len(vectors)
        
        return {
            "success": True,
            "synced": synced,
            "failed": failed,
            "total": total_to_sync,
            "message": f"Synced {synced}/{total_to_sync} vectors to Pinecone"
        }
        
    except Exception as e:
        logger.error(f"Batch sync failed: {e}")
        return {"success": False, "error": str(e)}


def test_vector_db_connection() -> Dict[str, Any]:
    """
    Test connectivity to the configured vector databases.
    
    Returns:
        Dict with connection test results
    """
    results = {
        "pgvector": {"status": "unknown"},
        "pinecone": {"status": "unknown"},
    }
    
    # Test PostgreSQL
    try:
        if connection.vendor == 'postgresql':
            from ..models import ContentAnalysis
            count = ContentAnalysis.objects.filter(embedding__isnull=False).count()
            results["pgvector"] = {
                "status": "connected",
                "embeddings_count": count,
                "database": "postgresql"
            }
        else:
            results["pgvector"] = {
                "status": "limited",
                "message": "SQLite detected - pgvector features unavailable"
            }
    except Exception as e:
        results["pgvector"] = {"status": "error", "error": str(e)}
    
    # Test Pinecone
    if settings.USE_PINECONE:
        try:
            from .pinecone_service import get_pinecone_service
            pc = get_pinecone_service()
            
            if pc.is_ready():
                stats = pc.get_stats()
                results["pinecone"] = {
                    "status": "connected",
                    "index_name": settings.PINECONE_INDEX_NAME,
                    "stats": stats
                }
            else:
                results["pinecone"] = {
                    "status": "not_configured",
                    "message": "Pinecone client not initialized (check API key)"
                }
        except Exception as e:
            results["pinecone"] = {"status": "error", "error": str(e)}
    else:
        results["pinecone"] = {"status": "disabled"}
    
    return results
