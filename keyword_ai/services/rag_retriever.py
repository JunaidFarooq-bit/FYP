"""
RAG (Retrieval-Augmented Generation) Service for Keyword AI

Provides semantic search capabilities to retrieve relevant historical
content analyses for augmenting LLM prompts with contextual knowledge.

Note: Full RAG with vector similarity requires PostgreSQL + pgvector.
On SQLite, RAG retrieval is skipped (graceful fallback).
"""

import numpy as np
import logging
from typing import List, Dict, Optional, Tuple
from django.db import models, connection
from ..models import ContentAnalysis, KeywordOpportunity

logger = logging.getLogger(__name__)


def retrieve_similar_analyses(
    content_embedding: np.ndarray,
    top_k: int = 5,
    min_quality_score: float = 50.0,
    include_keywords: bool = True
) -> List[Dict]:
    """
    Retrieve similar content analyses using vector similarity search.
    
    This is the core RAG retrieval function that finds historically similar
    content to augment LLM prompts with contextual knowledge.
    
    Args:
        content_embedding: The embedding vector of current content (384-dim)
        top_k: Number of similar analyses to retrieve
        min_quality_score: Minimum quality score filter (0-100)
        include_keywords: Whether to include top keywords from similar content
        
    Returns:
        List of dicts with similar analyses and their keywords
    """
    # RAG requires PostgreSQL with pgvector
    if connection.vendor != 'postgresql':
        logger.debug("RAG retrieval skipped: requires PostgreSQL with pgvector")
        return []
    
    if content_embedding is None or len(content_embedding) == 0:
        return []
    
    # Ensure embedding is list format for Django ORM
    if isinstance(content_embedding, np.ndarray):
        embedding_list = content_embedding.tolist()
    else:
        embedding_list = content_embedding
    
    # Use pgvector's distance operator (<-> for L2, <=> for cosine, <#> for inner product)
    # Cosine similarity is best for semantic similarity
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
        result = {
            'url': analysis.url,
            'quality_score': analysis.quality_score,
            'similarity_score': 1 - analysis.distance,  # Convert distance to similarity
            'analyzed_at': analysis.analyzed_at.isoformat(),
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


def retrieve_by_keyword_gap(
    current_keywords: List[str],
    target_keyword: str,
    top_k: int = 3
) -> List[Dict]:
    """
    Retrieve analyses that rank for target keyword but current content doesn't.
    
    Useful for competitor gap analysis and content improvement suggestions.
    
    Args:
        current_keywords: Keywords current content already targets
        target_keyword: The keyword we want to rank for
        top_k: Number of analyses to retrieve
        
    Returns:
        Analyses that successfully target the gap keyword
    """
    # Find analyses that have this keyword as an opportunity
    gap_opportunities = KeywordOpportunity.objects.filter(
        keyword__icontains=target_keyword,
        relevance_score__gte=70,
        is_rejected=False
    ).select_related('content_analysis').order_by('-relevance_score')[:top_k]
    
    results = []
    for opp in gap_opportunities:
        analysis = opp.content_analysis
        if analysis.embedding is not None:
            results.append({
                'url': analysis.url,
                'keyword': opp.keyword,
                'relevance_score': opp.relevance_score,
                'keyword_type': opp.keyword_type,
                'ai_reasoning': opp.ai_reasoning,
                'quality_score': analysis.quality_score
            })
    
    return results


def format_rag_context(
    retrieved_analyses: List[Dict],
    max_context_length: int = 2000
) -> str:
    """
    Format retrieved analyses into a context string for LLM prompts.
    
    Args:
        retrieved_analyses: Output from retrieve_similar_analyses()
        max_context_length: Maximum characters for context
        
    Returns:
        Formatted context string for LLM augmentation
    """
    if not retrieved_analyses:
        return "No similar historical analyses found."
    
    context_parts = []
    current_length = 0
    
    context_parts.append("## Similar Content References (RAG Context)\n")
    context_parts.append("The following similar content analyses provide context for better keyword suggestions:\n\n")
    
    for i, analysis in enumerate(retrieved_analyses, 1):
        section = f"### Reference {i}: {analysis.get('title', 'Untitled')}\n"
        section += f"- URL: {analysis['url'][:80]}\n"
        section += f"- Quality Score: {analysis['quality_score']:.1f}/100\n"
        section += f"- Similarity: {(analysis.get('similarity_score', 0) * 100):.1f}%\n"
        
        if 'top_keywords' in analysis and analysis['top_keywords']:
            section += "- Successful Keywords:\n"
            for kw in analysis['top_keywords'][:5]:
                section += f"  • {kw['keyword']} (score: {kw['score']:.1f}, {kw.get('intent', 'unknown')})\n"
        
        section += "\n"
        
        if current_length + len(section) > max_context_length:
            break
            
        context_parts.append(section)
        current_length += len(section)
    
    context_parts.append("\nUse the patterns from these successful analyses to inform your keyword suggestions.")
    
    return "".join(context_parts)


def build_augmented_prompt(
    base_prompt: str,
    content_embedding: np.ndarray,
    retrieval_kwargs: Optional[Dict] = None
) -> str:
    """
    Build an augmented LLM prompt with RAG context.
    
    This is the main entry point for RAG augmentation.
    
    Args:
        base_prompt: The original prompt without context
        content_embedding: Embedding of content to find similar analyses
        retrieval_kwargs: Additional args for retrieve_similar_analyses()
        
    Returns:
        Augmented prompt with retrieved context prepended
    """
    retrieval_kwargs = retrieval_kwargs or {}
    
    # Retrieve similar content
    similar_analyses = retrieve_similar_analyses(content_embedding, **retrieval_kwargs)
    
    # Format as context
    rag_context = format_rag_context(similar_analyses)
    
    # Combine: Context + Original Prompt
    augmented = f"{rag_context}\n\n{'='*60}\n\n{base_prompt}"
    
    return augmented


def get_hybrid_context(
    content_embedding: np.ndarray,
    current_keywords: List[str],
    page_topic: str = "",
    top_k_similar: int = 3,
    top_k_gaps: int = 2
) -> Dict[str, any]:
    """
    Get comprehensive RAG context combining multiple retrieval strategies.
    
    Returns structured context for different aspects of keyword analysis.
    
    Args:
        content_embedding: Current content embedding vector
        current_keywords: Already identified keywords
        page_topic: Topic description for gap analysis
        top_k_similar: Number of similar analyses
        top_k_gaps: Number of gap analyses
        
    Returns:
        Dict with 'similar_content', 'gap_opportunities', 'formatted_context'
    """
    # Retrieve similar successful content
    similar = retrieve_similar_analyses(
        content_embedding,
        top_k=top_k_similar,
        min_quality_score=60.0
    )
    
    # Identify potential keyword gaps
    gaps = []
    if page_topic and current_keywords:
        gaps = retrieve_by_keyword_gap(
            current_keywords,
            page_topic,
            top_k=top_k_gaps
        )
    
    # Build formatted context
    context_parts = []
    
    if similar:
        context_parts.append("## Similar High-Quality Content References\n")
        for s in similar:
            context_parts.append(f"- {s.get('title', 'Untitled')} (score: {s['quality_score']:.0f})\n")
            if s.get('top_keywords'):
                keywords_str = ", ".join([k['keyword'] for k in s['top_keywords'][:5]])
                context_parts.append(f"  Keywords: {keywords_str}\n")
    
    if gaps:
        context_parts.append("\n## Competitor Gap Opportunities\n")
        for g in gaps:
            context_parts.append(f"- Target: '{g['keyword']}' (relevance: {g['relevance_score']:.0f})\n")
            if g.get('ai_reasoning'):
                context_parts.append(f"  Why: {g['ai_reasoning'][:100]}...\n")
    
    return {
        'similar_content': similar,
        'gap_opportunities': gaps,
        'formatted_context': "".join(context_parts),
        'context_count': len(similar) + len(gaps)
    }
