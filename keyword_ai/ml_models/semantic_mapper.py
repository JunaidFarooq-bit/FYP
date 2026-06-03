"""
Content-to-Keyword Semantic Mapper (Phase 2)
Maps content semantics to keyword opportunities using bi-encoder architecture.
Uses FAISS for efficient similarity search.
"""

import os
import numpy as np
from typing import List, Dict, Tuple, Optional

# Optional FAISS import with fallback
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    faiss = None
    FAISS_AVAILABLE = False

from keyword_ai.services.embeddings import get_model as get_embedding_model

# Model paths
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
FAISS_INDEX_PATH = os.path.join(MODEL_DIR, "keyword_index.faiss")
KEYWORD_VOCAB_PATH = os.path.join(MODEL_DIR, "keyword_vocabulary.npy")

# Lazy-loaded models
_faiss_index = None
_keyword_vocabulary = None


class SemanticKeywordMapper:
    """
    Maps content to keywords using semantic similarity.
    
    Architecture:
    - Bi-encoder: Content encoder + Keyword encoder
    - FAISS index for fast similarity search
    - Cross-encoder for re-ranking (optional)
    """
    
    def __init__(self, keyword_vocabulary: List[str] = None):
        self.embedding_model = get_embedding_model()
        self.keyword_vocabulary = keyword_vocabulary or []
        self._faiss_index = None
        self._keyword_embeddings = None
        
        # Build or load index if vocabulary provided
        if self.keyword_vocabulary:
            self._build_index()
    
    def _build_index(self):
        """Build FAISS index from keyword vocabulary."""
        if not self.keyword_vocabulary:
            return
        
        if not FAISS_AVAILABLE:
            print("Warning: FAISS not available. Semantic keyword mapping will use fallback method.")
            return
        
        print(f"Building FAISS index for {len(self.keyword_vocabulary)} keywords...")
        
        # Encode all keywords
        self._keyword_embeddings = self.embedding_model.encode(
            self.keyword_vocabulary,
            convert_to_numpy=True,
            show_progress_bar=True,
            batch_size=32
        )
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(self._keyword_embeddings)
        
        # Build FAISS index (IndexFlatIP = Inner Product = Cosine Similarity for normalized vectors)
        dimension = self._keyword_embeddings.shape[1]
        self._faiss_index = faiss.IndexFlatIP(dimension)
        self._faiss_index.add(self._keyword_embeddings)
        
        print(f"FAISS index built: {self._faiss_index.ntotal} vectors, {dimension}D")
    
    def find_similar_keywords(
        self,
        content_text: str,
        top_k: int = 20,
        similarity_threshold: float = 0.3
    ) -> List[Dict]:
        """
        Find keywords semantically similar to content.
        
        Args:
            content_text: Page content to match
            top_k: Number of similar keywords to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of keyword dicts with similarity scores
        """
        if not FAISS_AVAILABLE:
            return []
        
        if self._faiss_index is None or self._faiss_index.ntotal == 0:
            return []
        
        # Encode content
        content_embedding = self.embedding_model.encode(
            content_text,
            convert_to_numpy=True
        ).reshape(1, -1)
        
        # Normalize
        faiss.normalize_L2(content_embedding)
        
        # Search FAISS index
        scores, indices = self._faiss_index.search(content_embedding, top_k)
        
        # Build results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= similarity_threshold and idx < len(self.keyword_vocabulary):
                results.append({
                    "keyword": self.keyword_vocabulary[idx],
                    "similarity_score": round(float(score), 4),
                    "match_type": "semantic",
                })
        
        return results
    
    def find_keyword_clusters(
        self,
        content_text: str,
        n_clusters: int = 5
    ) -> List[Dict]:
        """
        Find clusters of related keywords.
        
        Args:
            content_text: Page content
            n_clusters: Number of clusters to form
            
        Returns:
            List of clusters with representative keywords
        """
        if self._faiss_index is None or self._faiss_index.ntotal < n_clusters:
            return []
        
        # Get top N similar keywords
        candidates = self.find_similar_keywords(content_text, top_k=50, similarity_threshold=0.2)
        
        if len(candidates) < n_clusters:
            return []
        
        # Simple clustering by embedding similarity
        keywords = [c["keyword"] for c in candidates]
        embeddings = self.embedding_model.encode(keywords, convert_to_numpy=True)
        
        # K-means clustering
        from sklearn.cluster import KMeans
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        # Build clusters
        clusters = []
        for i in range(n_clusters):
            cluster_keywords = [
                {"keyword": keywords[j], "similarity": candidates[j]["similarity_score"]}
                for j in range(len(keywords))
                if cluster_labels[j] == i
            ]
            
            if cluster_keywords:
                # Sort by similarity
                cluster_keywords.sort(key=lambda x: x["similarity"], reverse=True)
                
                clusters.append({
                    "cluster_id": i,
                    "size": len(cluster_keywords),
                    "keywords": cluster_keywords[:10],  # Top 10 per cluster
                    "representative": cluster_keywords[0]["keyword"] if cluster_keywords else "",
                })
        
        # Sort clusters by size
        clusters.sort(key=lambda x: x["size"], reverse=True)
        
        return clusters
    
    def map_content_to_keywords(
        self,
        content_text: str,
        existing_keywords: List[str] = None,
        top_n: int = 30
    ) -> Dict:
        """
        Full mapping pipeline from content to keyword opportunities.
        
        Args:
            content_text: Page content
            existing_keywords: Keywords already targeting
            top_n: Number of opportunities to return
            
        Returns:
            Dict with mapped keywords, clusters, and analysis
        """
        # Find similar keywords from vocabulary
        similar_keywords = self.find_similar_keywords(content_text, top_k=top_n * 2)
        
        # Find clusters
        clusters = self.find_keyword_clusters(content_text, n_clusters=5)
        
        # Filter out existing keywords
        existing_set = set(kw.lower() for kw in (existing_keywords or []))
        new_keywords = [
            kw for kw in similar_keywords
            if kw["keyword"].lower() not in existing_set
        ]
        
        # Score and rank
        scored_keywords = self._score_keyword_opportunities(new_keywords[:top_n])
        
        return {
            "mapped_keywords": scored_keywords,
            "clusters": clusters,
            "total_matches": len(similar_keywords),
            "new_opportunities": len(new_keywords),
            "coverage_analysis": {
                "existing_keywords_count": len(existing_set),
                "mapped_keywords_count": len(scored_keywords),
                "potential_coverage": len(scored_keywords) / max(len(existing_set), 1),
            }
        }
    
    def _score_keyword_opportunities(self, keywords: List[Dict]) -> List[Dict]:
        """Score keyword opportunities for prioritization."""
        for kw in keywords:
            score = kw.get("similarity_score", 0) * 100
            
            # Length bonus (slight preference for medium length)
            word_count = len(kw["keyword"].split())
            if 2 <= word_count <= 5:
                score += 5
            
            # Specificity bonus
            if any(w in kw["keyword"].lower() for w in ['best', 'top', 'how', 'what', 'guide']):
                score += 3
            
            kw["opportunity_score"] = round(min(100, score), 2)
        
        # Sort by opportunity score
        keywords.sort(key=lambda x: x["opportunity_score"], reverse=True)
        return keywords
    
    def save_index(self, filepath: str = None):
        """Save FAISS index to disk."""
        if self._faiss_index is None:
            raise ValueError("No index to save")
        
        filepath = filepath or FAISS_INDEX_PATH
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        faiss.write_index(self._faiss_index, filepath)
        
        # Save vocabulary
        vocab_path = filepath.replace('.faiss', '_vocabulary.npy')
        np.save(vocab_path, np.array(self.keyword_vocabulary))
        
        print(f"Index saved to {filepath}")
        print(f"Vocabulary saved to {vocab_path}")
    
    @classmethod
    def load_index(cls, filepath: str = None):
        """Load FAISS index from disk."""
        filepath = filepath or FAISS_INDEX_PATH
        vocab_path = filepath.replace('.faiss', '_vocabulary.npy')
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Index not found: {filepath}")
        
        # Load vocabulary
        vocabulary = np.load(vocab_path, allow_pickle=True).tolist()
        
        # Create instance
        mapper = cls(vocabulary)
        
        # Load FAISS index
        mapper._faiss_index = faiss.read_index(filepath)
        
        print(f"Loaded index with {mapper._faiss_index.ntotal} keywords")
        return mapper


# Global vocabulary for SEO keywords (can be expanded)
DEFAULT_KEYWORD_VOCABULARY = [
    # SEO & Digital Marketing
    "seo tips", "seo strategy", "seo optimization", "seo guide",
    "digital marketing", "content marketing", "social media marketing",
    "email marketing", "affiliate marketing", "influencer marketing",
    "google ranking", "search engine optimization", "organic traffic",
    "keyword research", "backlink building", "link building strategy",
    "on page seo", "off page seo", "technical seo", "local seo",
    "seo audit", "seo tools", "seo analysis", "seo trends",
    
    # Content & Blogging
    "content strategy", "content creation", "blogging tips",
    "content writing", "copywriting", "content calendar",
    "blog post ideas", "article writing", "content marketing strategy",
    "evergreen content", "content optimization", "content promotion",
    
    # Business & Entrepreneurship
    "online business", "small business tips", "business growth",
    "startup marketing", "entrepreneurship", "business strategy",
    "lead generation", "conversion rate optimization", "sales funnel",
    "customer acquisition", "business branding", "personal branding",
    
    # E-commerce
    "ecommerce seo", "shopify tips", "woocommerce guide",
    "product page optimization", "online store marketing",
    "dropshipping guide", "amazon fba", "etsy marketing",
    
    # Analytics & Tools
    "google analytics", "google search console", "seo metrics",
    "website analytics", "traffic analysis", "conversion tracking",
    "ahrefs guide", "semrush tutorial", "moz pro",
    
    # Technical Web
    "website speed", "core web vitals", "mobile optimization",
    "wordpress seo", "web development", "ux design",
    "landing page optimization", "website migration", "https security",
]


def create_keyword_index(keyword_list: List[str] = None, save: bool = True):
    """
    Create and save FAISS keyword index.
    
    Args:
        keyword_list: List of keywords to index (uses default if None)
        save: Whether to save index to disk
        
    Returns:
        SemanticKeywordMapper instance
    """
    keywords = keyword_list or DEFAULT_KEYWORD_VOCABULARY
    
    mapper = SemanticKeywordMapper(keywords)
    
    if save:
        mapper.save_index()
    
    return mapper


def find_semantic_keywords(
    content_text: str,
    top_k: int = 20,
    use_cached_index: bool = True
) -> List[Dict]:
    """
    Convenience function to find semantically similar keywords.
    
    Args:
        content_text: Page content
        top_k: Number of keywords to return
        use_cached_index: Use saved index if available
        
    Returns:
        List of keyword dicts with similarity scores
    """
    mapper = None
    
    # Try to load cached index
    if use_cached_index and os.path.exists(FAISS_INDEX_PATH):
        try:
            mapper = SemanticKeywordMapper.load_index()
        except Exception as e:
            print(f"Failed to load index: {e}")
    
    # Create new index if needed
    if mapper is None:
        mapper = create_keyword_index(save=use_cached_index)
    
    return mapper.find_similar_keywords(content_text, top_k=top_k)


def compute_content_keyword_match(
    content_embedding: np.ndarray,
    keyword_embedding: np.ndarray
) -> float:
    """
    Compute cosine similarity between content and keyword.
    
    Args:
        content_embedding: Content embedding vector
        keyword_embedding: Keyword embedding vector
        
    Returns:
        Cosine similarity score (0-1)
    """
    return float(
        np.dot(content_embedding, keyword_embedding) / 
        (np.linalg.norm(content_embedding) * np.linalg.norm(keyword_embedding))
    )
