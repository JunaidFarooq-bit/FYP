"""
Main orchestrator that coordinates all analysis layers
"""

from .data_extraction import DataExtractor
from .semantic_analysis import SemanticAnalyzer
from .technical_analysis import TechnicalAnalyzer
from .authority_analysis import AuthorityAnalyzer
from .scoring_engine import ScoringEngine
from .gap_analyzer import GapAnalyzer


class ComparisonOrchestrator:
    """Coordinates the entire comparison analysis pipeline"""
    
    def __init__(self, url_primary, url_competitor, target_keyword=None):
        self.url_primary = url_primary
        self.url_competitor = url_competitor
        self.target_keyword = target_keyword
        
        # Initialize all service layers
        self.data_extractor = DataExtractor()
        self.semantic_analyzer = SemanticAnalyzer()
        self.technical_analyzer = TechnicalAnalyzer()
        self.authority_analyzer = AuthorityAnalyzer()
        self.scoring_engine = ScoringEngine()
        self.gap_analyzer = GapAnalyzer()
    
    def run_full_analysis(self):
        """Execute complete comparison analysis"""
        
        # LAYER 1: Extract raw data from both URLs
        primary_data = self.data_extractor.extract(self.url_primary)
        competitor_data = self.data_extractor.extract(self.url_competitor)
        
        # LAYER 2: Semantic & On-Page Analysis
        primary_semantic = self.semantic_analyzer.analyze(
            primary_data, 
            self.target_keyword
        )
        competitor_semantic = self.semantic_analyzer.analyze(
            competitor_data, 
            self.target_keyword
        )
        
        # LAYER 3: Technical SEO Analysis
        primary_technical = self.technical_analyzer.analyze(
            self.url_primary,
            primary_data
        )
        competitor_technical = self.technical_analyzer.analyze(
            self.url_competitor,
            competitor_data
        )
        
        # LAYER 4: Authority & Backlink Analysis
        primary_authority = self.authority_analyzer.analyze(
            self.url_primary,
            primary_data
        )
        competitor_authority = self.authority_analyzer.analyze(
            self.url_competitor,
            competitor_data
        )
        
        # LAYER 5: Calculate Scores
        primary_scores = self.scoring_engine.calculate_all_scores(
            semantic_data=primary_semantic,
            technical_data=primary_technical,
            authority_data=primary_authority,
            raw_data=primary_data
        )
        
        competitor_scores = self.scoring_engine.calculate_all_scores(
            semantic_data=competitor_semantic,
            technical_data=competitor_technical,
            authority_data=competitor_authority,
            raw_data=competitor_data
        )
        
        # LAYER 6: Gap Analysis & Explanation
        gap_analysis = self.gap_analyzer.analyze_gaps(
            primary_scores=primary_scores,
            competitor_scores=competitor_scores,
            primary_semantic=primary_semantic,
            competitor_semantic=competitor_semantic,
            primary_technical=primary_technical,
            competitor_technical=competitor_technical
        )
        
        # Compile results
        return {
            'primary': {
                'url': self.url_primary,
                'detected_keyword': primary_semantic['detected_keyword'],
                'intent_type': primary_semantic['intent_type'],
                'scores': primary_scores,
                'semantic': primary_semantic,
                'technical': primary_technical,
                'authority': primary_authority,
            },
            'competitor': {
                'url': self.url_competitor,
                'detected_keyword': competitor_semantic['detected_keyword'],
                'intent_type': competitor_semantic['intent_type'],
                'scores': competitor_scores,
                'semantic': competitor_semantic,
                'technical': competitor_technical,
                'authority': competitor_authority,
            },
            'gap_analysis': gap_analysis
        }