"""
Grammar and Spell Checking Service.
Provides comprehensive text analysis including spelling, grammar, and readability.
"""
import os
import re
import json
import logging
from typing import Dict, Any, List, Set, Optional
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
from django.http import JsonResponse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


class DictionaryManager:
    """Manages custom dictionary files for spell checking."""
    
    # Dictionary file names
    DICT_FILES = [
        'custom_dictionary.txt',
        'tech_terms.txt',
        'brand_names.txt',
        'pakistani_locations.txt',
        'user_ignored_words.txt'
    ]
    
    # Sample content for each dictionary
    SAMPLE_CONTENT = {
        'custom_dictionary.txt': '''# Common abbreviations and contractions
doesn
isn
wasn
hasn
haven
didn
wouldn
shouldn
couldn
aren
weren
won
don
ll
ve
re
''',
        'tech_terms.txt': '''# Technology and programming terms
app
apps
api
apis
css
html
javascript
js
python
reactjs
nodejs
github
docker
kubernetes
mongodb
postgresql
frontend
backend
fullstack
devops
seo
ui
ux
admin
analytics
shopify
wordpress
blockchain
saas
''',
        'brand_names.txt': '''# Company and product names
google
facebook
twitter
instagram
linkedin
amazon
microsoft
apple
shopify
stripe
paypal
zoom
slack
tabnine
copilot
''',
        'pakistani_locations.txt': '''# Pakistani cities and locations
karachi
lahore
islamabad
rawalpindi
faisalabad
multan
peshawar
quetta
hyderabad
sindh
punjab
balochistan
kpk
pakistan
pakistani
shahrah
clifton
defence
gulshan
saddar
''',
        'user_ignored_words.txt': '''# Words marked as correct by users
# This file is auto-updated when users click "Not a mistake"
# Add your custom words below:
codup
'''
    }
    
    def __init__(self, dict_dir: Optional[str] = None):
        if dict_dir is None:
            # Get the directory containing this file, then go up to SEOAnalyzer
            current_dir = Path(__file__).parent.parent
            self.dict_dir = current_dir / 'dictionaries'
        else:
            self.dict_dir = Path(dict_dir)
    
    def ensure_dictionaries(self) -> None:
        """Create dictionary directory and sample files if they don't exist."""
        self.dict_dir.mkdir(parents=True, exist_ok=True)
        
        for filename in self.DICT_FILES:
            filepath = self.dict_dir / filename
            if not filepath.exists():
                self._create_sample(filepath, filename)
    
    def _create_sample(self, filepath: Path, filename: str) -> None:
        """Create a sample dictionary file."""
        content = self.SAMPLE_CONTENT.get(filename, '# Custom dictionary words\n# Add one word per line\n')
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Created sample dictionary: {filepath}")
        except Exception as e:
            logger.warning(f"Could not create dictionary file {filename}: {e}")
    
    def load_words(self) -> Set[str]:
        """Load all custom words from dictionary files."""
        self.ensure_dictionaries()
        custom_words = set()
        
        for filename in self.DICT_FILES:
            filepath = self.dict_dir / filename
            if not filepath.exists():
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip().lower()
                        if line and not line.startswith('#'):
                            custom_words.add(line)
            except Exception as e:
                logger.warning(f"Could not load dictionary file {filename}: {e}")
        
        return custom_words
    
    def add_word(self, word: str) -> bool:
        """Add a word to the user-ignored-words dictionary."""
        word = word.strip().lower()
        if not word:
            return False
        
        self.ensure_dictionaries()
        filepath = self.dict_dir / 'user_ignored_words.txt'
        
        # Read existing words
        existing = set()
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                existing = {line.strip().lower() for line in f if line.strip() and not line.startswith('#')}
        
        if word in existing:
            return True  # Already exists
        
        # Append new word
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(f'\n{word}')
            return True
        except Exception as e:
            logger.error(f"Failed to add word to dictionary: {e}")
            return False


class GrammarAnalyzer:
    """
    Analyzes text for spelling errors, grammar issues, and readability.
    """
    
    # Grammar pattern constants
    PASSIVE_INDICATORS = [
        'is being', 'was being', 'has been', 'have been',
        'had been', 'will be', 'is done', 'was done', 'were being'
    ]
    
    GRAMMAR_PATTERNS = {
        r'\b(your)\s+(welcome)\b': "Use \"you're welcome\" (contraction of 'you are')",
        r'\b(should|could|would)\s+(of)\b': "Use 'have' instead of 'of' (should have, could have, would have)",
        r'\b(alot)\b': "Use 'a lot' (two words)",
        r'\bthere\s+(own|coming|going)\b': "Consider if 'their' or 'they're' is correct here",
    }
    
    # Common words to skip
    SKIP_WORDS = {'www', 'http', 'https', 'com', 'net', 'org', 'io', 'co', 'pk', 'edu', 'gov'}
    
    def __init__(self, custom_words: Optional[Set[str]] = None):
        self.dict_manager = DictionaryManager()
        self._custom_words = custom_words
        self._spell_checker = None
    
    def _get_spell_checker(self):
        """Lazy-load the spell checker."""
        if self._spell_checker is not None:
            return self._spell_checker
        
        try:
            from spellchecker import SpellChecker
            self._spell_checker = SpellChecker()
            
            # Load custom words
            if self._custom_words is None:
                self._custom_words = self.dict_manager.load_words()
            
            if self._custom_words:
                self._spell_checker.word_frequency.load_words(self._custom_words)
            
            return self._spell_checker
        except ImportError:
            logger.warning("pyspellchecker not installed. Run: pip install pyspellchecker")
            return None
    
    def analyze(self, soup: BeautifulSoup, min_content_length: int = 50) -> Dict[str, Any]:
        """
        Perform full grammar and spelling analysis.
        
        Args:
            soup: BeautifulSoup object containing page content
            min_content_length: Minimum content length to analyze
            
        Returns:
            Dict with grammar analysis results
        """
        # Extract text
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        try:
            text = soup.get_text(separator=' ', strip=True)
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return self._empty_result("Error extracting text")
        
        # Check content length
        if not text or len(text.strip()) < min_content_length:
            return {
                'grammar_verdict': 'Insufficient content for analysis',
                'grammar_score': 0,
                'spelling_errors': [],
                'grammar_issues': ['Content too short for meaningful analysis'],
                'readability_score': 0,
                'grammar_recommendations': ['Add more content (minimum 50 characters)']
            }
        
        spell = self._get_spell_checker()
        if spell is None:
            return self._empty_result("Spell checker not available")
        
        return self._analyze_text(text, spell)
    
    def _analyze_text(self, text: str, spell) -> Dict[str, Any]:
        """Core text analysis logic."""
        # Clean text
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Initialize tracking
        grammar_issues = []
        recommendations = []
        total_deductions = 0
        
        # Parse sentences and words
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        words_lower = [w.lower() for w in words]
        text_lower = text.lower()
        
        # --- SPELLING ANALYSIS ---
        spelling_errors = self._check_spelling(words, words_lower, spell)
        total_deductions += sum(err.get('deduction', 0) for err in spelling_errors)
        
        # Format spelling errors for display
        spelling_display = []
        for err in spelling_errors[:10]:
            count = err['count']
            if count > 1:
                display = f"'{err['word']}' → '{err['suggestion']}' ({count} occurrences)"
            else:
                display = f"'{err['word']}' → '{err['suggestion']}'"
            spelling_display.append({
                'word': err['word'],
                'suggestion': err['suggestion'],
                'count': count,
                'display': display
            })
        
        if len(spelling_errors) > 10:
            spelling_display.append({
                'display': f"... and {len(spelling_errors) - 10} more potential spelling issues",
                'word': None,
                'suggestion': None,
                'count': 0
            })
        
        if not spelling_display:
            spelling_display = [{
                'display': '✓ No spelling errors detected',
                'word': None,
                'suggestion': None,
                'count': 0
            }]
        
        # --- GRAMMAR CHECKS ---
        
        # 1. Repeated words
        word_pairs = [' '.join(words_lower[i:i+2]) for i in range(len(words_lower)-1)]
        repeated = [pair.split()[0] for pair in word_pairs if len(pair.split()) == 2 and pair.split()[0] == pair.split()[1]]
        if repeated:
            unique_repeated = list(set(repeated))[:5]
            grammar_issues.append(f"Repeated words detected: {', '.join(unique_repeated)}")
            total_deductions += len(set(repeated)) * 3
        
        # 2. Sentence length analysis
        long_sentences = [s for s in sentences if len(s.split()) > 30]
        if long_sentences:
            count = len(long_sentences)
            grammar_issues.append(f"{count} overly long sentence(s) detected (>30 words)")
            recommendations.append("Break long sentences for better readability")
            total_deductions += count * 2
        
        short_sentences = [s for s in sentences if 0 < len(s.split()) < 5]
        if len(short_sentences) > len(sentences) * 0.3 and len(sentences) > 5:
            grammar_issues.append("Too many short sentences - affects flow")
            recommendations.append("Combine short sentences for better rhythm")
            total_deductions += 3
        
        # 3. Passive voice detection
        passive_count = sum(text_lower.count(indicator) for indicator in self.PASSIVE_INDICATORS)
        if passive_count > 3:
            grammar_issues.append(f"Excessive passive voice detected ({passive_count} instances)")
            recommendations.append("Use active voice for stronger, clearer writing")
            total_deductions += passive_count
        
        # 4. Capitalization issues
        sentences_text = '. '.join(sentences)
        lowercase_starts = len(re.findall(r'\.\s+[a-z]', sentences_text))
        if lowercase_starts > 0:
            grammar_issues.append(f"{lowercase_starts} sentence(s) start with lowercase")
            total_deductions += lowercase_starts * 2
        
        # 5. Multiple punctuation
        multi_punct = len(re.findall(r'[!?]{2,}', text))
        if multi_punct > 0:
            grammar_issues.append("Multiple exclamation/question marks detected")
            recommendations.append("Use single punctuation marks for professionalism")
            total_deductions += multi_punct * 2
        
        # 6. Common grammar mistakes
        for pattern, suggestion in self.GRAMMAR_PATTERNS.items():
            matches = re.findall(pattern, text_lower)
            if matches:
                grammar_issues.append(f"{suggestion} - {len(matches)} instance(s)")
                total_deductions += len(matches) * 2
        
        # 7. Missing spaces after punctuation
        no_space_after_punct = len(re.findall(r'[.,;:][a-zA-Z]', text))
        if no_space_after_punct > 2:
            grammar_issues.append(f"Missing space after punctuation ({no_space_after_punct} instances)")
            total_deductions += no_space_after_punct
        
        # 8. Double spaces
        double_spaces = len(re.findall(r'\s{2,}', text))
        if double_spaces > 2:
            grammar_issues.append(f"Multiple spaces detected ({double_spaces} instances)")
            total_deductions += 1
        
        # --- READABILITY ANALYSIS ---
        if words and sentences:
            avg_word_length = sum(len(w) for w in words) / len(words)
            avg_sentence_length = len(words) / len(sentences)
            
            syllable_estimate = sum(max(1, len(re.findall(r'[aeiou]+', w.lower()))) for w in words)
            syllables_per_word = syllable_estimate / len(words)
            
            # Flesch Reading Ease score
            readability_score = 206.835 - 1.015 * avg_sentence_length - 84.6 * syllables_per_word
            readability_score = max(0, min(100, readability_score))
            
            if readability_score < 50:
                recommendations.append("Simplify language for better readability")
                total_deductions += 2
            elif readability_score > 80:
                recommendations.append("✓ Excellent readability - text is easy to understand")
        else:
            readability_score = 50
        
        # --- SEO RECOMMENDATIONS ---
        if len(words) < 300:
            recommendations.append("Consider adding more content (aim for 300+ words for SEO)")
        
        if not spelling_errors and not grammar_issues:
            recommendations.append("✓ Excellent writing quality - no issues detected")
        
        if len(spelling_errors) == 0:
            recommendations.append("✓ No spelling errors found")
        
        if passive_count == 0:
            recommendations.append("✓ Good use of active voice")
        
        # --- CALCULATE FINAL SCORE ---
        grammar_score = max(0, min(100, 100 - total_deductions))
        
        if grammar_score >= 90:
            verdict = "✓ Excellent - Professional writing quality"
        elif grammar_score >= 75:
            verdict = "✓ Good - Minor improvements possible"
        elif grammar_score >= 60:
            verdict = "⚠️ Fair - Several issues to address"
        else:
            verdict = "❌ Poor - Significant writing issues detected"
        
        return {
            'grammar_verdict': verdict,
            'grammar_score': round(grammar_score, 1),
            'spelling_errors': spelling_display,
            'grammar_issues': grammar_issues if grammar_issues else ['✓ No grammar issues detected'],
            'readability_score': round(readability_score, 1),
            'grammar_recommendations': recommendations if recommendations else ['✓ Content quality is excellent']
        }
    
    def _check_spelling(self, words: List[str], words_lower: List[str], spell) -> List[Dict]:
        """Check spelling and return errors with suggestions."""
        errors = []
        custom_words = self._custom_words or set()
        original_set = set(words)
        
        # Filter words to check
        words_to_check = []
        for word in words:
            word_lower = word.lower()
            
            if word_lower in custom_words:
                continue
            
            # Skip certain word patterns
            if (len(word) < 3 or 
                word.isupper() or 
                any(c.isdigit() for c in word) or
                any(c.isupper() for c in word[1:]) or
                word.endswith("'s") or
                "'" in word or
                word.isdigit()):
                continue
                
            if word_lower in self.SKIP_WORDS:
                continue
                
            words_to_check.append(word_lower)
        
        # Find misspelled words
        misspelled = spell.unknown(words_to_check)
        
        # Filter out proper nouns (capitalized words)
        for word in misspelled:
            capitalized = word.capitalize()
            if capitalized in original_set or word.upper() in original_set:
                continue
            
            correction = spell.correction(word)
            if correction and correction != word:
                # Validate correction similarity for longer words
                if len(word) > 4 and len(correction) > 4:
                    common_chars = set(word) & set(correction)
                    if len(common_chars) < len(word) * 0.5:
                        continue
                
                count = words_lower.count(word)
                errors.append({
                    'word': word,
                    'suggestion': correction,
                    'count': count,
                    'deduction': 2 * count
                })
        
        return errors
    
    def _empty_result(self, reason: str) -> Dict[str, Any]:
        """Return an empty result for when analysis can't be performed."""
        return {
            'grammar_verdict': 'Analysis unavailable',
            'grammar_score': 0,
            'spelling_errors': [],
            'grammar_issues': [reason],
            'readability_score': 0,
            'grammar_recommendations': ['Enable spell checker for analysis']
        }


# View function for adding words to dictionary (to be used in views.py)
@require_POST
def add_to_dictionary_view(request):
    """View function to add a word to the custom dictionary."""
    try:
        data = json.loads(request.body)
        word = data.get('word', '').strip().lower()
        
        if not word:
            return JsonResponse({'success': False, 'error': 'No word provided'})
        
        manager = DictionaryManager()
        
        if manager.add_word(word):
            return JsonResponse({
                'success': True,
                'word': word,
                'message': f"'{word}' added to dictionary"
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to add word'
            })
            
    except Exception as e:
        logger.error(f"Error adding word to dictionary: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
