"""
Layer 2: Semantic & On-Page Analysis with OpenAI GPT-4
Analyzes content quality, keyword usage, intent, and NLP features using AI
"""

import re
import json
from collections import Counter
from openai import OpenAI
from django.conf import settings
import tiktoken


class SemanticAnalyzer:
    """Analyze semantic and on-page SEO factors using OpenAI"""
    
    def __init__(self):
        print("\n" + "="*80)
        print("[SEMANTIC] Initializing SemanticAnalyzer...")
        print("="*80)
        
        # Get OpenAI/OpenRouter configuration
        api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        use_openrouter = getattr(settings, 'USE_OPENROUTER', False)
        
        print(f"[SEMANTIC] API Key present: {bool(api_key)}")
        print(f"[SEMANTIC] API Key starts with: {api_key[:15]}...")
        print(f"[SEMANTIC] Model: {self.model}")
        print(f"[SEMANTIC] USE_OPENROUTER: {use_openrouter}")
        
        # Initialize OpenAI client with correct base_url
        if use_openrouter:
            print("[SEMANTIC] Using OpenRouter API")
            print("[SEMANTIC] Base URL: https://openrouter.ai/api/v1")
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1"
            )
        else:
            print("[SEMANTIC] Using OpenAI API")
            print("[SEMANTIC] Base URL: https://api.openai.com/v1")
            self.client = OpenAI(api_key=api_key)
        
        # Token counter for cost management
        try:
            self.encoding = tiktoken.encoding_for_model(self.model)
            print(f"[SEMANTIC] Using encoding for model: {self.model}")
        except:
            self.encoding = tiktoken.get_encoding("cl100k_base")
            print(f"[SEMANTIC] Using default encoding: cl100k_base")
        
        print("[SEMANTIC] Initialization complete!")
        print("="*80 + "\n")
    
    def analyze(self, extracted_data, target_keyword=None):
        """Perform full semantic analysis using OpenAI"""
        
        print("\n" + "="*80)
        print("[SEMANTIC] Starting semantic analysis...")
        print("="*80)
        
        try:
            body_text = extracted_data['body_text']
            title = extracted_data['title']
            h1 = extracted_data['h1']
            headings = extracted_data['headings_all']
            word_count = extracted_data['word_count']
            
            print(f"[SEMANTIC] Title: {title}")
            print(f"[SEMANTIC] H1: {h1}")
            print(f"[SEMANTIC] Word count: {word_count}")
            print(f"[SEMANTIC] Headings count: {len(headings)}")
            print(f"[SEMANTIC] Body text length: {len(body_text)} chars")
            
            # Truncate content if too long (manage costs)
            print(f"\n[SEMANTIC] Truncating content to max 3000 tokens...")
            body_text_truncated = self._truncate_content(body_text, max_tokens=3000)
            print(f"[SEMANTIC] Truncated text length: {len(body_text_truncated)} chars")
            
            # Auto-detect primary keyword if not provided
            if not target_keyword:
                print(f"\n[SEMANTIC] No target keyword provided, auto-detecting...")
                detected_keyword = self._auto_detect_keyword_ai(title, h1, body_text_truncated)
                print(f"[SEMANTIC] Detected keyword: '{detected_keyword}'")
            else:
                detected_keyword = target_keyword
                print(f"[SEMANTIC] Using provided keyword: '{detected_keyword}'")
            
            # AI-powered analyses
            print(f"\n[SEMANTIC] Running comprehensive AI analysis...")
            ai_analysis = self._comprehensive_ai_analysis(
                title=title,
                h1=h1,
                body_text=body_text_truncated,
                headings=headings,
                target_keyword=detected_keyword
            )
            
            # Extract top ranking keywords from AI analysis
            top_keywords = ai_analysis.get('top_keywords', [])
            print(f"[SEMANTIC] Top keywords found: {len(top_keywords)}")
            
            # Search intent from AI
            intent_type = ai_analysis.get('intent_type', 'informational')
            print(f"[SEMANTIC] Intent type: {intent_type}")
            
            # Semantic keywords (LSI) from AI
            semantic_keywords = ai_analysis.get('semantic_keywords', [])
            print(f"[SEMANTIC] Semantic keywords found: {len(semantic_keywords)}")
            
            # Entities from AI
            entities = ai_analysis.get('entities', {})
            print(f"[SEMANTIC] Entities extracted: {sum(len(v) for v in entities.values())}")
            
            # Topic depth analysis
            print(f"\n[SEMANTIC] Analyzing topic depth...")
            topic_depth = self._analyze_topic_depth_ai(headings, body_text_truncated)
            print(f"[SEMANTIC] Topic depth score: {topic_depth['score']}/100")
            
            # E-E-A-T signals with AI enhancement
            print(f"\n[SEMANTIC] Analyzing E-E-A-T signals...")
            eeat_signals = self._analyze_eeat_signals_ai(extracted_data, body_text_truncated)
            print(f"[SEMANTIC] E-E-A-T score: {eeat_signals['score']}/100")
            
            # Content quality score from AI
            content_quality = ai_analysis.get('content_quality_score', 70)
            print(f"[SEMANTIC] Content quality: {content_quality}/100")
            
            # Keyword placement analysis (traditional)
            print(f"\n[SEMANTIC] Analyzing keyword placement...")
            keyword_in_title = detected_keyword.lower() in title.lower() if detected_keyword else False
            keyword_in_h1 = detected_keyword.lower() in h1.lower() if detected_keyword else False
            keyword_density = self._calculate_keyword_density(body_text, detected_keyword)
            
            print(f"[SEMANTIC] Keyword in title: {keyword_in_title}")
            print(f"[SEMANTIC] Keyword in H1: {keyword_in_h1}")
            print(f"[SEMANTIC] Keyword density: {keyword_density}%")
            
            # Readability from AI
            readability_score = ai_analysis.get('readability_score', 70)
            print(f"[SEMANTIC] Readability score: {readability_score}/100")
            
            # FAQ presence
            has_faq = extracted_data.get('has_faq', False)
            print(f"[SEMANTIC] Has FAQ: {has_faq}")
            
            # Content structure quality
            print(f"\n[SEMANTIC] Analyzing content structure...")
            structure_quality = self._analyze_content_structure(extracted_data)
            print(f"[SEMANTIC] Structure quality: {structure_quality['score']}/100")
            
            # Intent alignment score from AI
            intent_alignment = ai_analysis.get('intent_alignment_score', 70)
            print(f"[SEMANTIC] Intent alignment: {intent_alignment}/100")
            
            result = {
                'detected_keyword': detected_keyword,
                'top_keywords': top_keywords,
                'intent_type': intent_type,
                'intent_alignment_score': intent_alignment,
                'keyword_placement': {
                    'in_title': keyword_in_title,
                    'in_h1': keyword_in_h1,
                    'density': keyword_density,
                },
                'semantic_coverage': {
                    'keywords': semantic_keywords,
                    'coverage_score': min(len(semantic_keywords) * 10, 100)
                },
                'entities': entities,
                'topic_depth': topic_depth,
                'word_count': word_count,
                'readability_score': readability_score,
                'content_quality_score': content_quality,
                'eeat_signals': eeat_signals,
                'has_faq': has_faq,
                'structure_quality': structure_quality,
                'multimedia': {
                    'image_count': len(extracted_data.get('images', [])),
                    'video_count': extracted_data.get('videos', {}).get('count', 0)
                },
                'ai_insights': ai_analysis.get('insights', [])
            }
            
            print("\n" + "="*80)
            print(f"[SEMANTIC] Analysis complete!")
            print(f"[SEMANTIC] Overall quality score: {content_quality}/100")
            print("="*80 + "\n")
            
            return result
            
        except Exception as e:
            print(f"\n[SEMANTIC] CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            print("[SEMANTIC] Returning fallback result")
            return self._get_fallback_result(extracted_data)
    
    def _truncate_content(self, text, max_tokens=3000):
        """Truncate content to fit within token limits"""
        
        try:
            tokens = self.encoding.encode(text)
            
            if len(tokens) <= max_tokens:
                print(f"[SEMANTIC] Content within limit ({len(tokens)} tokens)")
                return text
            
            print(f"[SEMANTIC] Truncating from {len(tokens)} to {max_tokens} tokens")
            
            # Truncate to max_tokens
            truncated_tokens = tokens[:max_tokens]
            truncated_text = self.encoding.decode(truncated_tokens)
            
            return truncated_text
            
        except Exception as e:
            print(f"[SEMANTIC] Error truncating content: {e}")
            # Fallback: truncate by characters
            return text[:max_tokens * 4]
    
    def _auto_detect_keyword_ai(self, title, h1, body_text):
        """Auto-detect primary keyword using OpenAI"""
        
        print(f"[KEYWORD] Auto-detecting keyword...")
        
        prompt = f"""Analyze this web page content and identify the primary target keyword or key phrase (2-4 words).

Title: {title}
H1: {h1}
Content preview: {body_text[:500]}

Return ONLY the primary keyword/phrase, nothing else."""

        try:
            print(f"[KEYWORD] Sending request to AI...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an SEO expert analyzing web content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=50
            )
            
            keyword = response.choices[0].message.content.strip()
            print(f"[KEYWORD] AI detected: '{keyword}'")
            return keyword
            
        except Exception as e:
            print(f"[KEYWORD] ERROR: {e}")
            import traceback
            traceback.print_exc()
            print(f"[KEYWORD] Using fallback detection...")
            # Fallback to simple extraction
            fallback = self._fallback_keyword_detection(title, h1)
            print(f"[KEYWORD] Fallback detected: '{fallback}'")
            return fallback
    
    def _comprehensive_ai_analysis(self, title, h1, body_text, headings, target_keyword):
        """Comprehensive AI-powered content analysis"""
        
        print(f"[AI-ANALYSIS] Starting comprehensive analysis...")
        
        headings_text = "\n".join([f"{h['level'].upper()}: {h['text']}" for h in headings[:20]])
        
        prompt = f"""Analyze this web page for SEO. Provide a JSON response with the following:

TARGET KEYWORD: {target_keyword}

TITLE: {title}
H1: {h1}

HEADINGS:
{headings_text}

CONTENT (first 2000 chars):
{body_text[:2000]}

Provide JSON with:
{{
  "intent_type": "informational|commercial_investigation|transactional|navigational",
  "intent_alignment_score": 0-100,
  "top_keywords": [
    {{"keyword": "example", "relevance": 0-100}}
  ],
  "semantic_keywords": [
    {{"keyword": "related term", "relevance": 0-100}}
  ],
  "entities": {{
    "PERSON": ["name1", "name2"],
    "ORG": ["company1"],
    "PRODUCT": ["product1"],
    "LOCATION": ["place1"]
  }},
  "content_quality_score": 0-100,
  "readability_score": 0-100,
  "insights": [
    "insight1",
    "insight2"
  ]
}}

Base intent_alignment_score on how well content matches detected intent.
Content_quality_score on comprehensiveness, depth, accuracy signals.
Readability_score on clarity, sentence structure, vocabulary.
Return 5-7 top_keywords and 8-10 semantic_keywords.
Insights should be specific SEO observations."""

        try:
            print(f"[AI-ANALYSIS] Sending request (model: {self.model})...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert SEO analyst. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            print(f"[AI-ANALYSIS] Response received ({len(content)} chars)")
            
            analysis = json.loads(content)
            print(f"[AI-ANALYSIS] JSON parsed successfully")
            print(f"[AI-ANALYSIS] Intent: {analysis.get('intent_type')}")
            print(f"[AI-ANALYSIS] Quality score: {analysis.get('content_quality_score')}")
            
            return analysis
            
        except Exception as e:
            print(f"[AI-ANALYSIS] ERROR: {e}")
            import traceback
            traceback.print_exc()
            print(f"[AI-ANALYSIS] Returning fallback structure")
            
            # Return fallback structure
            return {
                'intent_type': 'informational',
                'intent_alignment_score': 70,
                'top_keywords': [],
                'semantic_keywords': [],
                'entities': {'PERSON': [], 'ORG': [], 'PRODUCT': [], 'LOCATION': []},
                'content_quality_score': 70,
                'readability_score': 70,
                'insights': []
            }
    
    def _analyze_topic_depth_ai(self, headings, body_text):
        """Analyze topic depth using AI"""
        
        print(f"[TOPIC-DEPTH] Analyzing topic depth...")
        
        headings_text = "\n".join([f"{h['level'].upper()}: {h['text']}" for h in headings[:15]])
        
        prompt = f"""Analyze the topic depth and coverage of this content.

HEADINGS:
{headings_text}

CONTENT PREVIEW:
{body_text[:1000]}

Provide JSON:
{{
  "depth_score": 0-100,
  "coverage_areas": ["topic1", "topic2", "topic3"],
  "missing_topics": ["topic1", "topic2"],
  "hierarchy_quality": 0-100
}}

depth_score: How thoroughly the topic is covered
hierarchy_quality: How well-organized the heading structure is"""

        try:
            print(f"[TOPIC-DEPTH] Sending request...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an SEO content analyst. Respond with JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            print(f"[TOPIC-DEPTH] Success! Score: {result.get('depth_score')}")
            
            return {
                'score': result.get('depth_score', 70),
                'depth_level': min(len(headings), 4),
                'coverage_areas': result.get('coverage_areas', []),
                'missing_topics': result.get('missing_topics', []),
                'hierarchy_quality': result.get('hierarchy_quality', 70)
            }
            
        except Exception as e:
            print(f"[TOPIC-DEPTH] ERROR: {e}")
            import traceback
            traceback.print_exc()
            print(f"[TOPIC-DEPTH] Using fallback")
            
            return {
                'score': 70,
                'depth_level': min(len(headings), 4),
                'coverage_areas': [],
                'missing_topics': [],
                'hierarchy_quality': 70
            }
    
    def _analyze_eeat_signals_ai(self, extracted_data, body_text):
        """Enhanced E-E-A-T analysis with AI"""
        
        print(f"[E-E-A-T] Analyzing E-E-A-T signals...")
        
        # Traditional signals
        traditional_signals = {
            'has_author': extracted_data.get('has_author', False),
            'has_date': extracted_data.get('has_date', False),
            'has_citations': self._detect_citations(extracted_data['soup']),
            'https_enabled': extracted_data.get('is_https', False),
        }
        
        print(f"[E-E-A-T] Traditional signals:")
        print(f"  - Author: {traditional_signals['has_author']}")
        print(f"  - Date: {traditional_signals['has_date']}")
        print(f"  - Citations: {traditional_signals['has_citations']}")
        print(f"  - HTTPS: {traditional_signals['https_enabled']}")
        
        # AI-enhanced E-E-A-T analysis
        prompt = f"""Analyze this content for E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) signals.

HAS AUTHOR: {traditional_signals['has_author']}
HAS DATE: {traditional_signals['has_date']}
HAS HTTPS: {traditional_signals['https_enabled']}

CONTENT PREVIEW:
{body_text[:1500]}

Provide JSON:
{{
  "experience_score": 0-100,
  "expertise_score": 0-100,
  "authoritativeness_score": 0-100,
  "trustworthiness_score": 0-100,
  "overall_eeat_score": 0-100,
  "signals_found": ["signal1", "signal2"],
  "recommendations": ["rec1", "rec2"]
}}

Look for:
- First-hand experience indicators
- Expert credentials or qualifications mentioned
- Citations, references, sources
- Professional tone and accuracy
- Transparent author information"""

        try:
            print(f"[E-E-A-T] Sending AI request...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an E-E-A-T assessment expert. Respond with JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=600,
                response_format={"type": "json_object"}
            )
            
            ai_eeat = json.loads(response.choices[0].message.content)
            print(f"[E-E-A-T] AI analysis complete")
            print(f"[E-E-A-T] Overall score: {ai_eeat.get('overall_eeat_score')}")
            
            # Combine traditional and AI signals
            return {
                **traditional_signals,
                'score': ai_eeat.get('overall_eeat_score', 70),
                'experience_score': ai_eeat.get('experience_score', 70),
                'expertise_score': ai_eeat.get('expertise_score', 70),
                'authoritativeness_score': ai_eeat.get('authoritativeness_score', 70),
                'trustworthiness_score': ai_eeat.get('trustworthiness_score', 70),
                'ai_signals': ai_eeat.get('signals_found', []),
                'ai_recommendations': ai_eeat.get('recommendations', [])
            }
            
        except Exception as e:
            print(f"[E-E-A-T] ERROR: {e}")
            import traceback
            traceback.print_exc()
            print(f"[E-E-A-T] Using traditional scoring")
            
            # Fallback to traditional scoring
            score = sum([
                20 if traditional_signals['has_author'] else 0,
                15 if traditional_signals['has_date'] else 0,
                25 if traditional_signals['has_citations'] else 0,
                15 if traditional_signals['https_enabled'] else 0,
            ])
            
            return {
                **traditional_signals,
                'score': score,
                'experience_score': score,
                'expertise_score': score,
                'authoritativeness_score': score,
                'trustworthiness_score': score,
                'ai_signals': [],
                'ai_recommendations': []
            }
    
    def _detect_citations(self, soup):
        """Detect presence of citations or references"""
        try:
            citation_indicators = [
                soup.find('ol', class_=re.compile(r'reference|citation', re.I)),
                soup.find('div', class_=re.compile(r'reference|citation', re.I)),
                soup.find(string=re.compile(r'References|Citations|Sources', re.I))
            ]
            return any(citation_indicators)
        except:
            return False
    
    def _analyze_content_structure(self, extracted_data):
        """Analyze content structure quality"""
        
        print(f"[STRUCTURE] Analyzing content structure...")
        
        try:
            headings = extracted_data.get('headings_all', [])
            paragraphs = extracted_data.get('paragraphs', [])
            
            h1_count = sum(1 for h in headings if h['level'] == 'h1')
            h2_count = sum(1 for h in headings if h['level'] == 'h2')
            
            print(f"[STRUCTURE] H1 count: {h1_count}")
            print(f"[STRUCTURE] H2 count: {h2_count}")
            print(f"[STRUCTURE] Paragraph count: {len(paragraphs)}")
            
            structure_score = 0
            
            if h1_count == 1:
                structure_score += 25
                print(f"[STRUCTURE] +25 points: Single H1")
            if h2_count >= 2:
                structure_score += 25
                print(f"[STRUCTURE] +25 points: Multiple H2s")
            if 5 <= len(paragraphs) <= 50:
                structure_score += 25
                print(f"[STRUCTURE] +25 points: Good paragraph count")
            if self._has_logical_heading_flow(headings):
                structure_score += 25
                print(f"[STRUCTURE] +25 points: Logical heading flow")
            
            print(f"[STRUCTURE] Total score: {structure_score}/100")
            
            return {
                'score': structure_score,
                'h1_count': h1_count,
                'h2_count': h2_count,
                'paragraph_count': len(paragraphs)
            }
            
        except Exception as e:
            print(f"[STRUCTURE] ERROR: {e}")
            return {
                'score': 0,
                'h1_count': 0,
                'h2_count': 0,
                'paragraph_count': 0
            }
    
    def _has_logical_heading_flow(self, headings):
        """Check if headings follow logical hierarchy"""
        if not headings:
            return False
        
        try:
            levels = [int(h['level'][1]) for h in headings]
            
            for i in range(len(levels) - 1):
                if levels[i + 1] - levels[i] > 1:
                    return False
            
            return True
        except:
            return False
    
    def _calculate_keyword_density(self, text, keyword):
        """Calculate keyword density percentage"""
        
        if not text or not keyword:
            return 0.0
        
        try:
            text_lower = text.lower()
            keyword_lower = keyword.lower()
            
            total_words = len(re.findall(r'\b\w+\b', text))
            
            if total_words == 0:
                return 0.0
            
            keyword_count = text_lower.count(keyword_lower)
            density = (keyword_count / total_words) * 100
            
            return round(density, 2)
        except:
            return 0.0
    
    def _fallback_keyword_detection(self, title, h1):
        """Fallback keyword detection without AI"""
        
        try:
            # Simple frequency-based detection
            text = f"{title} {h1}".lower()
            words = re.findall(r'\b[a-z]{3,}\b', text)
            
            # Remove stop words
            stop_words = {'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'for', 'with', 'from'}
            filtered = [w for w in words if w not in stop_words]
            
            if filtered:
                # Get most common word
                counter = Counter(filtered)
                return counter.most_common(1)[0][0]
            
            return 'unknown'
        except:
            return 'unknown'
    
    def _get_fallback_result(self, extracted_data):
        """Return fallback result when analysis fails"""
        
        print("[SEMANTIC] Generating fallback result...")
        
        return {
            'detected_keyword': 'unknown',
            'top_keywords': [],
            'intent_type': 'informational',
            'intent_alignment_score': 50,
            'keyword_placement': {
                'in_title': False,
                'in_h1': False,
                'density': 0.0,
            },
            'semantic_coverage': {
                'keywords': [],
                'coverage_score': 0
            },
            'entities': {'PERSON': [], 'ORG': [], 'PRODUCT': [], 'LOCATION': []},
            'topic_depth': {
                'score': 50,
                'depth_level': 0,
                'coverage_areas': [],
                'missing_topics': [],
                'hierarchy_quality': 50
            },
            'word_count': extracted_data.get('word_count', 0),
            'readability_score': 50,
            'content_quality_score': 50,
            'eeat_signals': {
                'has_author': False,
                'has_date': False,
                'has_citations': False,
                'https_enabled': False,
                'score': 0,
                'experience_score': 0,
                'expertise_score': 0,
                'authoritativeness_score': 0,
                'trustworthiness_score': 0,
                'ai_signals': [],
                'ai_recommendations': []
            },
            'has_faq': False,
            'structure_quality': {
                'score': 0,
                'h1_count': 0,
                'h2_count': 0,
                'paragraph_count': 0
            },
            'multimedia': {
                'image_count': 0,
                'video_count': 0
            },
            'ai_insights': ['Analysis failed - using fallback values']
        }
    