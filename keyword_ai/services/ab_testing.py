"""
A/B Testing Framework for Model Improvements (Phase 5)
Manages A/B tests between model variants.
"""

import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count

from ..models import ABTest, SuggestionFeedback, KeywordOpportunity


class ABTestManager:
    """
    Manages A/B tests for comparing model variants.
    """
    
    @staticmethod
    def create_test(
        test_name: str,
        control_model: str,
        treatment_model: str,
        traffic_split_percent: int = 50,
        test_description: str = "",
    ) -> ABTest:
        """
        Create a new A/B test.
        
        Args:
            test_name: Name of the test
            control_model: Control model variant
            treatment_model: Treatment model variant
            traffic_split_percent: Percentage of traffic to treatment (0-100)
            test_description: Optional description
            
        Returns:
            Created ABTest instance
        """
        return ABTest.objects.create(
            test_name=test_name,
            test_description=test_description,
            control_model=control_model,
            treatment_model=treatment_model,
            traffic_split_percent=traffic_split_percent,
            status='running',
        )
    
    @staticmethod
    def assign_variant(session_id: str, test: ABTest) -> str:
        """
        Assign a user to a test variant based on traffic split.
        
        Args:
            session_id: User session ID
            test: The A/B test
            
        Returns:
            Variant name: 'control' or 'treatment'
        """
        # Use session_id hash for consistent assignment
        hash_val = hash(session_id + str(test.id))
        
        # Assign based on traffic split
        if (hash_val % 100) < test.traffic_split_percent:
            return 'treatment'
        return 'control'
    
    @staticmethod
    def get_active_tests() -> List[ABTest]:
        """Get all currently running A/B tests."""
        return ABTest.objects.filter(status='running')
    
    @staticmethod
    def stop_test(test_id: int, winner: Optional[str] = None) -> Dict:
        """
        Stop an A/B test and optionally declare a winner.
        
        Args:
            test_id: The A/B test ID
            winner: 'control', 'treatment', or None for no winner
            
        Returns:
            Dict with test results
        """
        try:
            test = ABTest.objects.get(id=test_id)
            test.status = 'stopped'
            test.completed_at = timezone.now()
            
            if winner:
                test.winner = winner
            
            test.save()
            
            return {
                "success": True,
                "test_id": test_id,
                "status": "stopped",
                "winner": winner,
            }
            
        except ABTest.DoesNotExist:
            return {
                "success": False,
                "error": "Test not found"
            }
    
    @staticmethod
    def compute_test_results(test_id: int) -> Dict:
        """
        Compute statistical results for an A/B test.
        
        Returns:
            Dict with control/treatment metrics and statistical significance
        """
        try:
            test = ABTest.objects.get(id=test_id)
            
            # Get feedback from test period
            since = test.started_at
            if test.completed_at:
                until = test.completed_at
            else:
                until = timezone.now()
            
            # Aggregate feedback by variant
            # (This assumes we track which model variant generated each opportunity)
            # For now, we'll use a simplified approach
            
            control_metrics = {
                "total_opportunities": 0,
                "total_feedback": 0,
                "accepted": 0,
                "rejected": 0,
                "acceptance_rate": 0,
            }
            
            treatment_metrics = {
                "total_opportunities": 0,
                "total_feedback": 0,
                "accepted": 0,
                "rejected": 0,
                "acceptance_rate": 0,
            }
            
            # Calculate relative lift
            lift = 0
            if control_metrics["acceptance_rate"] > 0:
                lift = ((treatment_metrics["acceptance_rate"] - control_metrics["acceptance_rate"]) 
                        / control_metrics["acceptance_rate"] * 100)
            
            # Determine statistical significance (simplified)
            confidence = None
            if control_metrics["total_feedback"] > 30 and treatment_metrics["total_feedback"] > 30:
                # Simplified confidence calculation
                # In production, use proper statistical tests (t-test, chi-square)
                diff = abs(treatment_metrics["acceptance_rate"] - control_metrics["acceptance_rate"])
                if diff > 10:
                    confidence = 0.95
                elif diff > 5:
                    confidence = 0.90
                else:
                    confidence = 0.80
            
            # Update test with computed metrics
            test.control_metrics = control_metrics
            test.treatment_metrics = treatment_metrics
            test.confidence_level = confidence
            test.save()
            
            return {
                "test_id": test_id,
                "test_name": test.test_name,
                "status": test.status,
                "control": control_metrics,
                "treatment": treatment_metrics,
                "lift_percent": round(lift, 2),
                "confidence_level": confidence,
                "recommendation": ABTestManager._get_recommendation(lift, confidence),
            }
            
        except ABTest.DoesNotExist:
            return {"error": "Test not found"}
    
    @staticmethod
    def _get_recommendation(lift: float, confidence: Optional[float]) -> str:
        """Generate recommendation based on test results."""
        if confidence and confidence >= 0.95:
            if lift > 10:
                return "Strong evidence: Deploy treatment model"
            elif lift < -10:
                return "Strong evidence: Keep control model"
            else:
                return "No significant difference detected"
        elif confidence and confidence >= 0.90:
            if lift > 15:
                return "Moderate evidence: Consider deploying treatment"
            elif lift < -15:
                return "Moderate evidence: Keep control model"
            else:
                return "Inconclusive: Continue test or stop"
        else:
            return "Insufficient data: Continue test"
    
    @staticmethod
    def get_test_summary() -> List[Dict]:
        """Get summary of all A/B tests."""
        tests = ABTest.objects.all().order_by('-started_at')
        
        return [
            {
                "id": t.id,
                "name": t.test_name,
                "status": t.status,
                "control": t.control_model,
                "treatment": t.treatment_model,
                "traffic_split": t.traffic_split_percent,
                "winner": t.winner,
                "confidence": t.confidence_level,
                "started": t.started_at.strftime('%Y-%m-%d'),
                "duration_days": (t.completed_at - t.started_at).days if t.completed_at else 
                                (timezone.now() - t.started_at).days,
            }
            for t in tests
        ]


class ModelVariantRouter:
    """
    Routes users to different model variants for A/B testing.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.assigned_variants = {}
    
    def get_model_for_task(self, task: str, default_model: str) -> str:
        """
        Get the appropriate model for a task, considering A/B tests.
        
        Args:
            task: The task type (e.g., 'keyword_extraction', 'scoring')
            default_model: Default model to use if no active test
            
        Returns:
            Model name to use
        """
        # Check for active A/B tests for this task
        active_tests = ABTestManager.get_active_tests()
        
        for test in active_tests:
            # Check if this test applies to the task
            if task in test.test_name.lower() or task in test.test_description.lower():
                # Assign variant
                variant = ABTestManager.assign_variant(self.session_id, test)
                
                # Store assignment
                self.assigned_variants[test.id] = variant
                
                # Return appropriate model
                if variant == 'treatment':
                    return test.treatment_model
                else:
                    return test.control_model
        
        # No active test, use default
        return default_model
    
    def get_assignment_summary(self) -> Dict:
        """Get summary of variant assignments for this session."""
        return {
            "session_id": self.session_id[:8],
            "assignments": self.assigned_variants,
            "tests_participating": len(self.assigned_variants),
        }
