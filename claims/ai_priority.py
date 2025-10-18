"""
AI-powered claim priority detection
Analyzes claim descriptions to automatically set priority
"""
import logging
from django.conf import settings
from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)


class ClaimPriorityAI:
    """AI service for automatic claim priority detection"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'HUGGINGFACE_API_KEY', None)
        if not self.api_key:
            logger.warning("HUGGINGFACE_API_KEY not set - using keyword-based priority detection")
            self.client = None
        else:
            try:
                self.client = InferenceClient(token=self.api_key, timeout=30)
                logger.info("Hugging Face InferenceClient initialized for priority detection")
            except Exception as e:
                logger.error(f"Failed to initialize Hugging Face client: {e}")
                self.client = None
    
    def detect_priority(self, description: str) -> str:
        """
        Analyze claim description and return priority (Low, Medium, High)
        
        Args:
            description: The claim description text
            
        Returns:
            Priority level: 'Low', 'Medium', or 'High'
        """
        if not description or not description.strip():
            return 'Medium'  # Default for empty descriptions
        
        # Try AI-based detection first
        if self.client:
            try:
                priority = self._ai_detect_priority(description)
                logger.info(f"AI detected priority: {priority} for description: {description[:50]}...")
                return priority
            except Exception as e:
                logger.warning(f"AI priority detection failed, falling back to keyword-based: {e}")
        
        # Fallback to keyword-based detection
        return self._keyword_based_priority(description)
    
    def _ai_detect_priority(self, description: str) -> str:
        """Use AI to detect priority based on description severity"""
        
        # Define priority categories
        categories = [
            "Low priority - minor issue, cosmetic damage, can wait",
            "Medium priority - moderate issue, affects functionality but not critical",
            "High priority - severe issue, complete failure, urgent, dangerous, safety concern"
        ]
        
        # Use zero-shot classification
        result = self.client.zero_shot_classification(
            text=description,
            labels=categories,
            model="facebook/bart-large-mnli"
        )
        
        # Parse result - it returns a list of dicts with label and score
        if result:
            # Get the highest scoring category
            best_match = max(result, key=lambda x: x['score'])
            label = best_match['label']
            score = best_match['score']
            
            logger.info(f"AI classification: {label} (confidence: {score:.2f})")
            
            # Map to priority
            if "High priority" in label:
                return 'High'
            elif "Medium priority" in label:
                return 'Medium'
            else:
                return 'Low'
        
        return 'Medium'  # Default
    
    def _keyword_based_priority(self, description: str) -> str:
        """
        Fallback: Keyword-based priority detection
        Analyzes urgency keywords in the description
        """
        description_lower = description.lower()
        
        # High priority keywords - urgent, dangerous, severe issues
        high_keywords = [
            'urgent', 'emergency', 'immediately', 'asap', 'critical', 'severe',
            'dangerous', 'unsafe', 'hazard', 'fire', 'smoke', 'burning', 'explode',
            'completely broken', 'not working at all', 'dead', 'won\'t turn on',
            'safety', 'injury', 'hurt', 'electric shock', 'sparking',
            'stopped working', 'completely failed', 'unusable', 'can\'t use'
        ]
        
        # Medium priority keywords - functional issues
        medium_keywords = [
            'malfunction', 'defect', 'problem', 'issue', 'broken', 'damaged',
            'not working properly', 'battery', 'charging', 'overheating',
            'screen cracked', 'display', 'camera', 'audio', 'connectivity',
            'performance', 'slow', 'freezing', 'crashing', 'error'
        ]
        
        # Low priority keywords - minor issues
        low_keywords = [
            'cosmetic', 'scratch', 'minor', 'small', 'slight', 'tiny',
            'discoloration', 'aesthetic', 'appearance', 'not urgent'
        ]
        
        # Check for high priority
        for keyword in high_keywords:
            if keyword in description_lower:
                logger.info(f"Keyword-based priority: High (matched: {keyword})")
                return 'High'
        
        # Check for low priority
        for keyword in low_keywords:
            if keyword in description_lower:
                logger.info(f"Keyword-based priority: Low (matched: {keyword})")
                return 'Low'
        
        # Check for medium priority or default to medium
        for keyword in medium_keywords:
            if keyword in description_lower:
                logger.info(f"Keyword-based priority: Medium (matched: {keyword})")
                return 'Medium'
        
        logger.info("Keyword-based priority: Medium (default)")
        return 'Medium'  # Default priority


# Global instance
priority_detector = ClaimPriorityAI()

