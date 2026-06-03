"""
Content Analysis Service - Extracted from Website_Audit class
Handles content quality, readability, and text analysis.
"""
import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ContentAnalysisService:
    """Service for analyzing website content quality and readability."""
    
    def __init__(self, html_content: str):
        from bs4 import BeautifulSoup
        if isinstance(html_content, str):
            self.soup = BeautifulSoup(html_content, 'html.parser') if html_content else None
        else:
            self.soup = html_content
        self.response = html_content
        self.data = {}
        
    def analyze_content_quality(self) -> Dict[str, Any]:
        """Analyze overall content quality metrics."""
        try:
            result = {
                'word_count': self._get_word_count(),
                'readability': {'flesch_reading_ease': self._calculate_readability()},
                'content_structure': self._analyze_structure(),
                'quality_score': 0
            }
            
            # Calculate overall quality score
            result['content_quality_score'] = self._calculate_quality_score(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in content quality analysis: {e}")
            return {
                'word_count': 0,
                'readability_score': 0,
                'content_structure': {},
                'content_quality_score': 0
            }
    
    def _get_word_count(self) -> int:
        """Count words in the page content."""
        try:
            if not self.soup:
                return 0
            
            # Remove script and style elements
            for script in self.soup(["script", "style", "noscript"]):
                script.decompose()
            
            text = self.soup.get_text(separator=' ', strip=True)
            words = text.split()
            return len(words)
            
        except Exception as e:
            logger.error(f"Error counting words: {e}")
            return 0
    
    def _calculate_readability(self) -> float:
        """Calculate readability score (simplified Flesch-Kincaid)."""
        try:
            text = self.soup.get_text(separator=' ', strip=True) if self.soup else ""
            
            if not text or len(text.strip()) < 50:
                return 0
            
            words = text.split()
            sentences = text.split('.')
            
            word_count = len(words)
            sentence_count = len([s for s in sentences if s.strip()])
            
            if sentence_count == 0:
                return 0
            
            # Simplified readability calculation
            avg_words_per_sentence = word_count / sentence_count
            readability_score = max(0, min(100, 120 - (avg_words_per_sentence * 2)))
            
            return round(readability_score, 1)
            
        except Exception as e:
            logger.error(f"Error calculating readability: {e}")
            return 0
    
    def _analyze_structure(self) -> Dict[str, Any]:
        """Analyze content structure (headings, paragraphs, lists)."""
        try:
            if not self.soup:
                return {}
            
            structure = {
                'headings': {
                    'h1': len(self.soup.find_all('h1')),
                    'h2': len(self.soup.find_all('h2')),
                    'h3': len(self.soup.find_all('h3')),
                    'h4': len(self.soup.find_all('h4')),
                    'h5': len(self.soup.find_all('h5')),
                    'h6': len(self.soup.find_all('h6')),
                },
                'paragraphs': len(self.soup.find_all('p')),
                'lists': {
                    'ul': len(self.soup.find_all('ul')),
                    'ol': len(self.soup.find_all('ol')),
                },
                'images': len(self.soup.find_all('img')),
                'links': len(self.soup.find_all('a')),
            }
            
            return structure
            
        except Exception as e:
            logger.error(f"Error analyzing structure: {e}")
            return {}
    
    def _calculate_quality_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall content quality score."""
        try:
            score = 0
            
            # Word count scoring (0-30 points)
            word_count = metrics.get('word_count', 0)
            if word_count >= 300:
                score += 30
            elif word_count >= 150:
                score += 20
            elif word_count >= 50:
                score += 10
            
            # Readability scoring (0-30 points)
            readability = metrics.get('readability_score', 0)
            score += min(30, readability * 0.3)
            
            # Structure scoring (0-40 points)
            structure = metrics.get('content_structure', {})
            if structure:
                h1_count = structure.get('headings', {}).get('h1', 0)
                h2_count = structure.get('headings', {}).get('h2', 0)
                paragraph_count = structure.get('paragraphs', 0)
                
                if h1_count > 0:
                    score += 15
                if h2_count > 0:
                    score += 10
                if paragraph_count > 0:
                    score += 15
            
            return round(min(100, score), 1)
            
        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return 0
    
    def extract_text_content(self) -> str:
        """Extract clean text content from the page."""
        try:
            if not self.soup:
                return ""
            
            # Remove unwanted elements
            for element in self.soup(["script", "style", "noscript", "nav", "footer"]):
                element.decompose()
            
            text = self.soup.get_text(separator=' ', strip=True)
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text content: {e}")
            return ""
