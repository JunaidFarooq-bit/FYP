"""
SEO Analyzer Services Package.
Provides modular services for different aspects of SEO analysis.
"""
from .eeat_analyzer import EEATAnalyzer
from .grammar_analyzer import GrammarAnalyzer, DictionaryManager, add_to_dictionary_view
from .link_checker import LinkService, LinkAnalyzer, BrokenLinkChecker
from .minification_checker import (
    MinificationChecker, 
    CSSMinificationChecker, 
    JSMinificationChecker,
    MinificationService
)
from .technical_audit import (
    TechnicalAuditService,
    SchemaAnalyzer,
    OpenGraphAnalyzer,
    FaviconAnalyzer,
    RobotsAnalyzer,
    SitemapAnalyzer
)

__all__ = [
    'EEATAnalyzer',
    'GrammarAnalyzer',
    'DictionaryManager',
    'add_to_dictionary_view',
    'LinkService',
    'LinkAnalyzer',
    'BrokenLinkChecker',
    'MinificationChecker',
    'CSSMinificationChecker',
    'JSMinificationChecker',
    'MinificationService',
    'TechnicalAuditService',
    'SchemaAnalyzer',
    'OpenGraphAnalyzer',
    'FaviconAnalyzer',
    'RobotsAnalyzer',
    'SitemapAnalyzer',
]
