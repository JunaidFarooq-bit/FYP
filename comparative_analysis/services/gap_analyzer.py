"""
Gap Analysis & Explanation Engine with OpenAI Enhancement
Generates human-readable explanations of SEO gaps
"""

import json
import logging
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)


class GapAnalyzer:
    """Analyze gaps between URLs and generate AI-powered explanations"""
    
    def __init__(self):
        use_groq = getattr(settings, 'USE_GROQ', True)
        use_openrouter = getattr(settings, 'USE_OPENROUTER', False)

        if use_groq:
            api_key = getattr(settings, 'GROQ_API_KEY', '') or ''
            self.model = getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
            base_url = "https://api.groq.com/openai/v1"
            provider = "groq"
        elif use_openrouter:
            api_key = getattr(settings, 'OPENROUTER_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', '') or ''
            self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
            base_url = "https://openrouter.ai/api/v1"
            provider = "openrouter"
        else:
            api_key = getattr(settings, 'OPENAI_API_KEY', '') or ''
            self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
            base_url = None
            provider = "openai"

        logger.info(f"[GAP] Initializing (provider={provider}, model={self.model})")

        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)
    
    def analyze_gaps(self, primary_scores, competitor_scores, 
                     primary_semantic, competitor_semantic,
                     primary_technical, competitor_technical):
        """Generate comprehensive gap analysis with AI enhancement"""
        
        logger.info("[GAP] Starting gap analysis")
        
        try:
            score_gaps = self._calculate_score_gaps(primary_scores, competitor_scores)
            ranking_factors = self._identify_ranking_factors(
                score_gaps,
                primary_semantic,
                competitor_semantic,
                primary_technical,
                competitor_technical
            )
            explanation = self._generate_ai_explanation(
                score_gaps,
                ranking_factors,
                primary_scores,
                competitor_scores,
                primary_semantic,
                competitor_semantic
            )
            summary = self._generate_summary(score_gaps, ranking_factors)
            ranking_gap_score = self._calculate_ranking_gap(score_gaps)
            
            logger.info(f"[GAP] Complete — factors={len(ranking_factors)}, gap_score={ranking_gap_score}")
            return {
                'score_gaps': score_gaps,
                'ranking_factors': ranking_factors,
                'explanation': explanation,
                'summary': summary,
                'ranking_gap_score': ranking_gap_score
            }
        except Exception as e:
            logger.exception(f"[GAP] Error in analyze_gaps(): {e}")
            return self._get_fallback_result()
    
    def _generate_ai_explanation(self, score_gaps, ranking_factors, 
                                 primary_scores, competitor_scores,
                                 primary_semantic, competitor_semantic):
        """Generate detailed explanation using AI"""
        
        overall_gap = score_gaps.get('overall_seo_strength', {})
        winner = overall_gap.get('winner', 'tie')
        
        gap_summary = {
            'winner': winner,
            'overall_score_primary': primary_scores.get('overall_seo_strength', 0),
            'overall_score_competitor': competitor_scores.get('overall_seo_strength', 0),
            'score_differences': {
                k: v['gap'] for k, v in score_gaps.items()
            },
            'primary_keyword': primary_semantic.get('detected_keyword', ''),
            'competitor_keyword': competitor_semantic.get('detected_keyword', ''),
            'primary_intent': primary_semantic.get('intent_type', ''),
            'competitor_intent': competitor_semantic.get('intent_type', ''),
            'top_gaps': ranking_factors[:3]
        }
        
        prompt = f"""You are an SEO expert explaining why one URL ranks better than another.

COMPARISON DATA:
{json.dumps(gap_summary, indent=2)}

Respond ONLY with a valid JSON object, no markdown, no backticks, no extra text.

Return this exact structure:
{{
  "opening": "1-2 sentence summary of who is winning and by how much",
  "reasons": [
    {{"title": "Reason title", "detail": "Specific explanation with numbers"}},
    {{"title": "Reason title", "detail": "Specific explanation with numbers"}},
    {{"title": "Reason title", "detail": "Specific explanation with numbers"}}
  ],
  "recommendations": [
    {{"title": "Action title", "detail": "Specific step to take"}},
    {{"title": "Action title", "detail": "Specific step to take"}},
    {{"title": "Action title", "detail": "Specific step to take"}},
    {{"title": "Action title", "detail": "Specific step to take"}},
    {{"title": "Action title", "detail": "Specific step to take"}}
  ]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a senior SEO consultant providing gap analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.dumps(json.loads(raw))
        except Exception as e:
            logger.warning(f"[GAP-AI] AI explanation failed: {e}")
            return self._generate_traditional_explanation(
                score_gaps, ranking_factors, primary_scores, competitor_scores
            )
    
    def _generate_traditional_explanation(self, score_gaps, ranking_factors, 
                                         primary_scores, competitor_scores):
        """Traditional explanation generation (fallback)"""
        
        try:
            overall_gap = score_gaps.get('overall_seo_strength', {})
            winner = overall_gap.get('winner', 'tie')
            primary_overall = primary_scores.get('overall_seo_strength', 0)
            competitor_overall = competitor_scores.get('overall_seo_strength', 0)
            
            if winner == 'competitor':
                explanation = f"The competitor URL ranks higher (overall SEO strength: {competitor_overall} vs {primary_overall}) primarily because:\n\n"
            elif winner == 'primary':
                explanation = f"Your primary URL is stronger (overall SEO strength: {primary_overall} vs {competitor_overall}) primarily because:\n\n"
            else:
                explanation = "Both URLs have similar SEO strength.\n\n"
            
            for i, factor in enumerate(ranking_factors[:3], 1):
                category_name = factor['category'].replace('_', ' ').title()
                explanation += f"{i}. **{category_name}** "
                if factor['winner'] == 'competitor':
                    explanation += f"({abs(factor['gap'])} point advantage)\n"
                else:
                    explanation += f"(Your advantage: {abs(factor['gap'])} points)\n"
                for detail in factor['details']:
                    explanation += f"   \u2022 {detail}\n"
                explanation += "\n"
            
            if winner == 'competitor':
                explanation += "\n**Recommended Improvements:**\n"
                explanation += self._generate_recommendations(ranking_factors)
            
            return explanation
        except Exception as e:
            logger.warning(f"[GAP-FALLBACK] Error: {e}")
            return "Gap analysis completed. See score details for comparison."
    
    def _calculate_score_gaps(self, primary_scores, competitor_scores):
        """Calculate differences in all score categories"""
        
        gaps = {}
        
        for key in primary_scores:
            primary_val = primary_scores.get(key, 0)
            competitor_val = competitor_scores.get(key, 0)
            
            gap = competitor_val - primary_val
            gap_percentage = (abs(gap) / max(primary_val, 1)) * 100
            
            if gap > 0:
                winner = 'competitor'
            elif gap < 0:
                winner = 'primary'
            else:
                winner = 'tie'
            
            gaps[key] = {
                'primary': primary_val,
                'competitor': competitor_val,
                'gap': gap,
                'gap_percentage': gap_percentage,
                'winner': winner
            }
        
        return gaps
    
    def _identify_ranking_factors(self, score_gaps, primary_semantic, 
                                  competitor_semantic, primary_technical, 
                                  competitor_technical):
        """Identify the most significant ranking factors"""
        
        factors = []
        
        sorted_gaps = sorted(
            score_gaps.items(),
            key=lambda x: abs(x[1]['gap']),
            reverse=True
        )
        
        for score_name, gap_data in sorted_gaps[:5]:
            if abs(gap_data['gap']) > 5 and gap_data['winner'] != 'tie':
                
                factor = {
                    'category': score_name,
                    'gap': gap_data['gap'],
                    'winner': gap_data['winner'],
                    'details': self._get_factor_details(
                        score_name,
                        gap_data,
                        primary_semantic,
                        competitor_semantic,
                        primary_technical,
                        competitor_technical
                    )
                }
                
                factors.append(factor)
        
        return factors
    
    def _get_factor_details(self, score_name, gap_data, primary_semantic, 
                           competitor_semantic, primary_technical, 
                           competitor_technical):
        """Get detailed explanation for a specific factor"""
        
        details = []
        
        try:  # noqa: SIM105
            if score_name == 'content_depth_score':
                primary_wc = primary_semantic.get('word_count', 0)
                competitor_wc = competitor_semantic.get('word_count', 0)
                
                if competitor_wc > primary_wc and primary_wc > 0:
                    details.append(f"{int((competitor_wc - primary_wc) / primary_wc * 100)}% more content ({competitor_wc} vs {primary_wc} words)")
                
                details.append("More comprehensive topic coverage")
            
            elif score_name == 'technical_score':
                primary_speed = primary_technical.get('page_speed', {}).get('load_time', 0)
                competitor_speed = competitor_technical.get('page_speed', {}).get('load_time', 0)
                
                if competitor_speed < primary_speed and competitor_speed > 0:
                    details.append(f"Faster load speed ({competitor_speed:.2f}s vs {primary_speed:.2f}s)")
                
                if competitor_technical.get('mobile_responsive') and not primary_technical.get('mobile_responsive'):
                    details.append("Mobile-responsive design")
            
            elif score_name == 'intent_alignment_score':
                details.append("Better alignment with search intent")
                
                primary_intent = primary_semantic.get('intent_type', '')
                competitor_intent = competitor_semantic.get('intent_type', '')
                
                if primary_intent != competitor_intent:
                    details.append(f"Intent mismatch: {primary_intent} vs {competitor_intent}")
            
            elif score_name == 'on_page_score':
                primary_kw = primary_semantic.get('keyword_placement', {})
                competitor_kw = competitor_semantic.get('keyword_placement', {})
                
                if competitor_kw.get('in_title') and not primary_kw.get('in_title'):
                    details.append("Keyword in title tag")
                
                if competitor_kw.get('in_h1') and not primary_kw.get('in_h1'):
                    details.append("Keyword in H1")
            
        except Exception as e:
            logger.debug(f"[GAP-DETAILS] Error for {score_name}: {e}")
        
        return details if details else ["Overall stronger performance in this category"]
    
    def _generate_recommendations(self, ranking_factors):
        """Generate actionable recommendations"""
        
        recommendations = ""
        
        for factor in ranking_factors[:3]:
            if factor['winner'] == 'competitor':
                category = factor['category']
                
                if category == 'content_depth_score':
                    recommendations += "• Expand content with more comprehensive coverage\n"
                    recommendations += "• Add FAQ section\n"
                    recommendations += "• Include more multimedia elements\n"
                
                elif category == 'technical_score':
                    recommendations += "• Improve page load speed\n"
                    recommendations += "• Ensure mobile responsiveness\n"
                    recommendations += "• Add structured data markup\n"
                
                elif category == 'on_page_score':
                    recommendations += "• Optimize title tag with primary keyword\n"
                    recommendations += "• Improve H1 tag optimization\n"
                    recommendations += "• Add semantic keywords throughout content\n"
        
        return recommendations
    
    def _generate_summary(self, score_gaps, ranking_factors):
        """Generate concise gap summary"""
        
        try:
            overall_gap = score_gaps.get('overall_seo_strength', {})
            winner = overall_gap.get('winner', 'tie')
            
            if not ranking_factors:
                return "Both URLs have similar SEO performance across all categories."
            
            top_factor = ranking_factors[0]
            category_name = top_factor['category'].replace('_', ' ').title()
            
            if winner == 'competitor':
                summary = f"Competitor leads primarily in {category_name}. "
                summary += f"Overall SEO gap: {abs(overall_gap.get('gap', 0))} points. "
                summary += f"Top improvement areas: {', '.join([f['category'].replace('_', ' ') for f in ranking_factors[:3]])}."
            elif winner == 'primary':
                summary = f"Your URL leads primarily in {category_name}. "
                summary += f"Overall advantage: {abs(overall_gap.get('gap', 0))} points."
            else:
                summary = "Both URLs are competitively matched."
            
            return summary
        except Exception as e:
            logger.warning(f"[GAP-SUMMARY] Error: {e}")
            return "Gap analysis completed."
    
    def _calculate_ranking_gap(self, score_gaps):
        """Calculate overall ranking gap score (0-100)"""
        
        try:
            overall_gap = score_gaps.get('overall_seo_strength', {})
            return int(min(abs(overall_gap.get('gap', 0)), 100))
        except Exception as e:
            logger.warning(f"[GAP-SCORE] Error: {e}")
            return 0
    
    def _get_fallback_result(self):
        """Return safe fallback result when analysis fails"""
        
        return {
            'score_gaps': {},
            'ranking_factors': [],
            'explanation': 'Gap analysis could not be completed. Please check the data and try again.',
            'summary': 'Analysis unavailable',
            'ranking_gap_score': 0
        }