"""
Feedback Collection & Analytics Service (Phase 5)
Tracks user interactions, collects feedback, and computes performance metrics.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from django.db.models import Avg, Count, Q
from django.utils import timezone

from ..models import (
    SuggestionFeedback,
    KeywordOpportunity,
    ModelPerformance,
    UserSessionMetrics,
    ContentAnalysis,
)


class FeedbackCollector:
    """
    Collects and manages user feedback on keyword suggestions.
    """
    
    @staticmethod
    def record_feedback(
        opportunity_id: int,
        user_action: str,
        user_comment: str = "",
        rating: Optional[int] = None,
        session_id: str = "",
        time_spent_seconds: Optional[int] = None,
    ) -> Dict:
        """
        Record user feedback on a keyword suggestion.
        
        Args:
            opportunity_id: The KeywordOpportunity ID
            user_action: 'accepted', 'rejected', 'implemented', 'ignored'
            user_comment: Optional user comment
            rating: Optional 1-5 star rating
            session_id: User session identifier
            time_spent_seconds: Time user spent considering this suggestion
            
        Returns:
            Dict with feedback record details
        """
        try:
            opportunity = KeywordOpportunity.objects.get(id=opportunity_id)
            
            # Update opportunity status
            if user_action in ['accepted', 'implemented']:
                opportunity.is_accepted = True
                opportunity.is_rejected = False
            elif user_action == 'rejected':
                opportunity.is_accepted = False
                opportunity.is_rejected = True
            
            opportunity.save()
            
            # Create feedback record
            feedback = SuggestionFeedback.objects.create(
                opportunity=opportunity,
                user_action=user_action,
                user_comment=user_comment,
                rating=rating,
                session_id=session_id,
            )
            
            # Update session metrics
            FeedbackCollector._update_session_metrics(
                session_id, 
                feedback_submitted=True,
                time_spent=time_spent_seconds
            )
            
            return {
                "success": True,
                "feedback_id": feedback.id,
                "opportunity_id": opportunity_id,
                "action": user_action,
                "message": f"Feedback recorded: {user_action}"
            }
            
        except KeywordOpportunity.DoesNotExist:
            return {
                "success": False,
                "error": "Opportunity not found"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def _update_session_metrics(session_id: str, feedback_submitted: bool = False, time_spent: Optional[int] = None):
        """Update aggregated session metrics."""
        if not session_id:
            return
        
        metrics, created = UserSessionMetrics.objects.get_or_create(
            session_id=session_id,
            defaults={
                "total_feedback_submitted": 1 if feedback_submitted else 0,
                "avg_time_on_page": time_spent,
            }
        )
        
        if not created:
            if feedback_submitted:
                metrics.total_feedback_submitted += 1
            if time_spent:
                # Update rolling average
                if metrics.avg_time_on_page:
                    metrics.avg_time_on_page = (metrics.avg_time_on_page + time_spent) // 2
                else:
                    metrics.avg_time_on_page = time_spent
            metrics.save()
    
    @staticmethod
    def get_opportunity_feedback_summary(opportunity_id: int) -> Dict:
        """Get feedback summary for a specific keyword opportunity."""
        try:
            opportunity = KeywordOpportunity.objects.get(id=opportunity_id)
            
            feedbacks = SuggestionFeedback.objects.filter(opportunity=opportunity)
            
            total = feedbacks.count()
            if total == 0:
                return {
                    "opportunity_id": opportunity_id,
                    "keyword": opportunity.keyword,
                    "total_feedback": 0,
                    "actions": {},
                    "avg_rating": None,
                }
            
            # Count actions
            actions = feedbacks.values('user_action').annotate(count=Count('user_action'))
            action_counts = {a['user_action']: a['count'] for a in actions}
            
            # Calculate average rating
            avg_rating = feedbacks.filter(rating__isnull=False).aggregate(
                avg=Avg('rating')
            )['avg']
            
            return {
                "opportunity_id": opportunity_id,
                "keyword": opportunity.keyword,
                "total_feedback": total,
                "actions": action_counts,
                "avg_rating": round(avg_rating, 2) if avg_rating else None,
                "latest_feedback": feedbacks.first().timestamp if feedbacks.exists() else None,
            }
            
        except KeywordOpportunity.DoesNotExist:
            return {"error": "Opportunity not found"}
    
    @staticmethod
    def get_feedback_by_keyword_type(keyword_type: str, days: int = 30) -> Dict:
        """Get aggregated feedback for a keyword type."""
        since = timezone.now() - timedelta(days=days)
        
        opportunities = KeywordOpportunity.objects.filter(
            keyword_type=keyword_type,
            created_at__gte=since
        )
        
        feedbacks = SuggestionFeedback.objects.filter(
            opportunity__in=opportunities
        )
        
        total = feedbacks.count()
        if total == 0:
            return {
                "keyword_type": keyword_type,
                "total_feedback": 0,
                "acceptance_rate": 0,
            }
        
        # Calculate acceptance rate
        accepted = feedbacks.filter(user_action__in=['accepted', 'implemented']).count()
        rejected = feedbacks.filter(user_action='rejected').count()
        
        total_with_action = accepted + rejected
        acceptance_rate = (accepted / total_with_action * 100) if total_with_action > 0 else 0
        
        return {
            "keyword_type": keyword_type,
            "total_opportunities": opportunities.count(),
            "total_feedback": total,
            "accepted": accepted,
            "rejected": rejected,
            "acceptance_rate": round(acceptance_rate, 2),
            "period_days": days,
        }


class PerformanceTracker:
    """
    Tracks and computes model performance metrics.
    """
    
    @staticmethod
    def record_prediction(model_name: str, model_version: str, opportunity_id: int):
        """Record that a model made a prediction."""
        # Get or create today's performance record
        today = timezone.now().date()
        
        performance, created = ModelPerformance.objects.get_or_create(
            model_name=model_name,
            model_version=model_version,
            recorded_at__date=today,
            defaults={
                "total_predictions": 1,
            }
        )
        
        if not created:
            performance.total_predictions += 1
            performance.save()
    
    @staticmethod
    def update_model_metrics(model_name: str, model_version: str):
        """
        Recompute metrics for a model based on recent feedback.
        """
        # Get all feedback for opportunities created by this model
        # (This assumes we track which model generated each opportunity)
        
        recent_feedback = SuggestionFeedback.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=7)
        )
        
        total = recent_feedback.count()
        if total == 0:
            return None
        
        accepted = recent_feedback.filter(user_action__in=['accepted', 'implemented']).count()
        rejected = recent_feedback.filter(user_action='rejected').count()
        ignored = recent_feedback.filter(user_action='ignored').count()
        
        avg_rating = recent_feedback.filter(rating__isnull=False).aggregate(
            avg=Avg('rating')
        )['avg']
        
        # Update or create performance record
        performance, created = ModelPerformance.objects.get_or_create(
            model_name=model_name,
            model_version=model_version,
            recorded_at__date=timezone.now().date(),
            defaults={
                "total_predictions": total,
                "accepted_suggestions": accepted,
                "rejected_suggestions": rejected,
                "ignored_suggestions": ignored,
                "avg_user_rating": avg_rating,
            }
        )
        
        if not created:
            performance.total_predictions = total
            performance.accepted_suggestions = accepted
            performance.rejected_suggestions = rejected
            performance.ignored_suggestions = ignored
            performance.avg_user_rating = avg_rating
            performance.save()
        
        return {
            "model_name": model_name,
            "model_version": model_version,
            "acceptance_rate": performance.acceptance_rate,
            "engagement_rate": performance.engagement_rate,
            "total_predictions": total,
        }
    
    @staticmethod
    def get_model_performance_history(model_name: str, days: int = 30) -> List[Dict]:
        """Get performance history for a model."""
        since = timezone.now() - timedelta(days=days)
        
        performances = ModelPerformance.objects.filter(
            model_name=model_name,
            recorded_at__gte=since
        ).order_by('recorded_at')
        
        return [
            {
                "date": p.recorded_at.strftime('%Y-%m-%d'),
                "version": p.model_version,
                "total_predictions": p.total_predictions,
                "acceptance_rate": p.acceptance_rate,
                "engagement_rate": p.engagement_rate,
                "avg_rating": p.avg_user_rating,
            }
            for p in performances
        ]
    
    @staticmethod
    def compare_models(model_names: List[str], days: int = 30) -> Dict:
        """Compare performance of multiple models."""
        since = timezone.now() - timedelta(days=days)
        
        comparison = {}
        for name in model_names:
            perf = ModelPerformance.objects.filter(
                model_name=name,
                recorded_at__gte=since
            ).order_by('-recorded_at').first()
            
            if perf:
                comparison[name] = {
                    "version": perf.model_version,
                    "acceptance_rate": perf.acceptance_rate,
                    "engagement_rate": perf.engagement_rate,
                    "total_predictions": perf.total_predictions,
                    "avg_rating": perf.avg_user_rating,
                }
        
        return comparison
    
    @staticmethod
    def get_system_health() -> Dict:
        """Get overall system health metrics."""
        since = timezone.now() - timedelta(days=7)
        
        # Feedback metrics
        total_feedback = SuggestionFeedback.objects.filter(timestamp__gte=since).count()
        accepted = SuggestionFeedback.objects.filter(
            timestamp__gte=since,
            user_action__in=['accepted', 'implemented']
        ).count()
        
        # Content analysis metrics
        total_analyses = ContentAnalysis.objects.filter(analyzed_at__gte=since).count()
        
        # Opportunity metrics
        total_opportunities = KeywordOpportunity.objects.filter(created_at__gte=since).count()
        accepted_opps = KeywordOpportunity.objects.filter(
            created_at__gte=since,
            is_accepted=True
        ).count()
        
        acceptance_rate = (accepted / total_feedback * 100) if total_feedback > 0 else 0
        opportunity_acceptance = (accepted_opps / total_opportunities * 100) if total_opportunities > 0 else 0
        
        return {
            "period_days": 7,
            "total_feedback": total_feedback,
            "total_analyses": total_analyses,
            "total_opportunities": total_opportunities,
            "feedback_acceptance_rate": round(acceptance_rate, 2),
            "opportunity_acceptance_rate": round(opportunity_acceptance_rate, 2),
            "system_health": "healthy" if acceptance_rate > 60 else "needs_improvement",
        }


class ContinuousLearningMonitor:
    """
    Monitors when models should be retrained based on feedback thresholds.
    """
    
    RETRAIN_THRESHOLDS = {
        "min_feedback_samples": 20,
        "min_acceptance_rate": 60,  # Percentage
        "max_days_since_retrain": 30,
    }
    
    @staticmethod
    def should_retrain(model_name: str) -> Dict:
        """
        Determine if a model should be retrained based on collected feedback.
        
        Returns:
            Dict with decision and reasoning
        """
        since = timezone.now() - timedelta(days=30)
        
        # Get recent feedback
        recent_feedback = SuggestionFeedback.objects.filter(
            timestamp__gte=since,
            user_action__in=["accepted", "implemented", "rejected"],
        )
        
        total_feedback = recent_feedback.count()
        
        if total_feedback < ContinuousLearningMonitor.RETRAIN_THRESHOLDS["min_feedback_samples"]:
            return {
                "should_retrain": False,
                "reason": f"Insufficient feedback samples ({total_feedback} < {ContinuousLearningMonitor.RETRAIN_THRESHOLDS['min_feedback_samples']})",
                "feedback_count": total_feedback,
            }
        
        # Check acceptance rate
        accepted = recent_feedback.filter(user_action__in=['accepted', 'implemented']).count()
        rejected = recent_feedback.filter(user_action='rejected').count()
        
        total_with_action = accepted + rejected
        if total_with_action > 0:
            acceptance_rate = (accepted / total_with_action) * 100
            
            if acceptance_rate < ContinuousLearningMonitor.RETRAIN_THRESHOLDS["min_acceptance_rate"]:
                return {
                    "should_retrain": True,
                    "reason": f"Acceptance rate ({acceptance_rate:.1f}%) below threshold ({ContinuousLearningMonitor.RETRAIN_THRESHOLDS['min_acceptance_rate']}%)",
                    "acceptance_rate": round(acceptance_rate, 2),
                    "feedback_count": total_feedback,
                    "urgency": "high" if acceptance_rate < 40 else "medium",
                }
        
        return {
            "should_retrain": False,
            "reason": "Performance within acceptable thresholds",
            "acceptance_rate": round((accepted / total_with_action * 100), 2) if total_with_action > 0 else 0,
            "feedback_count": total_feedback,
        }
    
    @staticmethod
    def get_retraining_recommendations() -> List[Dict]:
        """Get recommendations for which models need retraining."""
        models_to_check = [
            "relevance_scorer_v2",
            "suggestion_generator",
            "semantic_mapper",
        ]
        
        recommendations = []
        for model in models_to_check:
            result = ContinuousLearningMonitor.should_retrain(model)
            if result["should_retrain"]:
                recommendations.append({
                    "model": model,
                    **result
                })
        
        return recommendations
