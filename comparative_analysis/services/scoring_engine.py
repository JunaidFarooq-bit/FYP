"""
Layer 5: Scoring Engine
Calculates all SEO scores and overall rankings
"""


class ScoringEngine:
    """Calculate all SEO scores"""
    
    def calculate_all_scores(self, semantic_data, technical_data, authority_data, raw_data):
        """Calculate all scoring categories"""
        
        # 1. On-Page Score
        on_page_score = self._calculate_on_page_score(semantic_data, raw_data)
        
        # 2. Technical Score
        technical_score = technical_data['technical_score']
        
        # 3. Authority Score
        authority_score = authority_data['authority_score']
        
        # 4. Content Depth Score
        content_depth_score = self._calculate_content_depth_score(semantic_data, raw_data)
        
        # 5. UX Score
        ux_score = self._calculate_ux_score(semantic_data, technical_data, raw_data)
        
        # 6. Intent Alignment Score
        intent_alignment_score = semantic_data['intent_alignment_score']
        
        # 7. Backlink Strength Score
        backlink_strength_score = self._calculate_backlink_score(authority_data)
        
        # Overall SEO Strength Score
        overall_score = self._calculate_overall_score({
            'on_page': on_page_score,
            'technical': technical_score,
            'authority': authority_score,
            'content_depth': content_depth_score,
            'ux': ux_score,
            'intent_alignment': intent_alignment_score,
            'backlink': backlink_strength_score
        })
        
        return {
            'on_page_score': on_page_score,
            'technical_score': technical_score,
            'authority_score': authority_score,
            'content_depth_score': content_depth_score,
            'ux_score': ux_score,
            'intent_alignment_score': intent_alignment_score,
            'backlink_strength_score': backlink_strength_score,
            'overall_seo_strength': overall_score,
        }
    
    def _calculate_on_page_score(self, semantic_data, raw_data):
        """Calculate on-page SEO score (0-100)"""
        
        score = 0
        
        # Title tag quality (15 points)
        title = raw_data.get('title', '')
        if title:
            score += 10
            if 30 <= len(title) <= 60:
                score += 5
        
        # H1 presence (10 points)
        if raw_data.get('h1'):
            score += 10
        
        # Primary keyword placement (20 points)
        kw_placement = semantic_data.get('keyword_placement', {})
        score += 10 if kw_placement.get('in_title') else 0
        score += 10 if kw_placement.get('in_h1') else 0
        
        # Keyword density (5 points)
        density = kw_placement.get('density', 0)
        if 0.5 <= density <= 2.5:
            score += 5
        
        # Semantic keyword coverage (15 points)
        semantic_score = semantic_data.get('semantic_coverage', {}).get('coverage_score', 0)
        score += min(semantic_score, 15)
        
        # Meta description (5 points)
        if raw_data.get('meta_description'):
            score += 5
        
        # Word count (10 points)
        word_count = semantic_data.get('word_count', 0)
        if word_count >= 300:
            score += 5
        if word_count >= 1000:
            score += 5
        
        # Readability (10 points)
        readability = semantic_data.get('readability_score', 0)
        score += (readability / 100) * 10
        
        # E-E-A-T signals (10 points)
        eeat_score = semantic_data.get('eeat_signals', {}).get('score', 0)
        score += (eeat_score / 100) * 10
        
        return int(min(score, 100))
    
    def _calculate_content_depth_score(self, semantic_data, raw_data):
        """Calculate content depth and comprehensiveness score (0-100)"""
        
        score = 0
        
        # Word count depth (30 points)
        word_count = semantic_data.get('word_count', 0)
        if word_count >= 2000:
            score += 30
        elif word_count >= 1500:
            score += 25
        elif word_count >= 1000:
            score += 20
        elif word_count >= 500:
            score += 10
        
        # Topic depth (heading structure) (25 points)
        topic_depth = semantic_data.get('topic_depth', {})
        heading_score = topic_depth.get('score', 0) if isinstance(topic_depth, dict) else 0
        score += (heading_score / 100) * 25
        
        # FAQ presence (15 points)
        if semantic_data.get('has_faq'):
            score += 15
        
        # Multimedia usage (15 points)
        multimedia = semantic_data.get('multimedia', {})
        if multimedia.get('image_count', 0) > 0:
            score += 8
        if multimedia.get('video_count', 0) > 0:
            score += 7
        
        # Internal links (15 points)
        internal_links = len(raw_data.get('internal_links', []))
        if internal_links >= 10:
            score += 15
        elif internal_links >= 5:
            score += 10
        elif internal_links >= 2:
            score += 5
        
        return int(min(score, 100))
    
    def _calculate_ux_score(self, semantic_data, technical_data, raw_data):
        """Calculate user experience score (0-100)"""
        
        score = 0
        
        # Page speed (30 points)
        speed_score = technical_data.get('page_speed', {}).get('speed_score', 0)
        score += (speed_score / 100) * 30
        
        # Mobile responsiveness (25 points)
        if technical_data.get('mobile_responsive'):
            score += 25
        
        # Heading hierarchy (15 points)
        structure = semantic_data.get('structure_quality', {})
        structure_score = structure.get('score', 0) if isinstance(structure, dict) else 0
        score += (structure_score / 100) * 15
        
        # Readability (15 points)
        readability = semantic_data.get('readability_score', 0)
        score += (readability / 100) * 15
        
        # Content formatting (15 points)
        paragraph_count = structure.get('paragraph_count', 0) if isinstance(structure, dict) else 0
        if 5 <= paragraph_count <= 30:
            score += 15
        elif paragraph_count > 0:
            score += 8
        
        return int(min(score, 100))
    
    def _calculate_backlink_score(self, authority_data):
        """Calculate backlink strength score (0-100)"""
        
        # Use authority score as proxy
        authority = authority_data.get('authority_score', 0)
        
        # Use internal link strength
        internal = authority_data.get('internal_link_strength', {}).get('score', 0)
        
        # Weighted average
        score = (authority * 0.7) + (internal * 0.3)
        
        return int(min(score, 100))
    
    def _calculate_overall_score(self, scores):
        """Calculate weighted overall SEO strength score"""
        
        # Weighted calculation
        overall = (
            scores['on_page'] * 0.20 +
            scores['technical'] * 0.15 +
            scores['authority'] * 0.20 +
            scores['content_depth'] * 0.15 +
            scores['ux'] * 0.10 +
            scores['intent_alignment'] * 0.10 +
            scores['backlink'] * 0.10
        )
        
        return int(min(overall, 100))