"""
AI Service for analyzing claims data and generating insights for retailers
Uses Hugging Face Inference API for text analysis
"""

import os
from typing import List, Dict, Any
from collections import Counter
from django.conf import settings
from huggingface_hub import InferenceClient
import logging

logger = logging.getLogger(__name__)


class ClaimAnalyticsAI:
    """
    AI-powered analytics service for claim insights
    """
    
    def __init__(self):
        """Initialize Hugging Face Inference Client"""
        self.api_key = getattr(settings, 'HUGGINGFACE_API_KEY', None)
        if not self.api_key:
            logger.warning("HUGGINGFACE_API_KEY not set in settings")
            self.client = None
        else:
            try:
                self.client = InferenceClient(
                    token=self.api_key,
                    timeout=30
                )
                logger.info("Hugging Face InferenceClient initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Hugging Face client: {e}")
                self.client = None
        
        # Classification categories for claim reasons
        self.claim_categories = [
            "Battery issue",
            "Screen damage",
            "Hardware malfunction",
            "Software problem",
            "Water damage",
            "Charging issue",
            "Audio problem",
            "Performance issue",
            "Overheating",
            "Physical damage",
            "Other"
        ]
        
        # Categories for rejection reasons
        self.rejection_categories = [
            "Physical damage not covered",
            "Warranty expired",
            "Misuse or abuse",
            "Missing documentation",
            "Normal wear and tear",
            "Unauthorized repairs",
            "Liquid damage",
            "User error",
            "Cosmetic damage",
            "Insufficient evidence",
            "Other"
        ]
    
    def classify_text(self, text: str, categories: List[str]) -> Dict[str, float]:
        """
        Classify text into given categories using zero-shot classification
        Returns probabilities for each category
        """
        if not self.client or not text:
            return {}
        
        try:
            # Use zero-shot classification with bart-large-mnli
            result = self.client.zero_shot_classification(
                text=text,
                labels=categories,
                model="facebook/bart-large-mnli"
            )
            
            # Result is a list of dicts: [{'label': 'X', 'score': 0.9}, ...]
            # Convert to dictionary of category: score
            scores = {}
            for item in result:
                scores[item['label']] = item['score']
            
            return scores
            
        except Exception as e:
            logger.error(f"Error in zero-shot classification: {e}")
            return {}
    
    def analyze_claim_reasons(self, claims_data: List[Dict]) -> Dict[str, Any]:
        """
        Analyze claim descriptions and categorize reasons
        """
        if not self.client or not claims_data:
            return self._get_fallback_claim_analysis(claims_data)
        
        category_counts = Counter()
        category_products = {}
        
        for claim in claims_data:
            # Combine issue summary and description for better classification
            text = f"{claim['issue_summary']} {claim['detailed_description']}"
            
            # Classify the claim
            scores = self.classify_text(text, self.claim_categories)
            
            if scores:
                # Get the top category
                top_category = max(scores.items(), key=lambda x: x[1])[0]
                category_counts[top_category] += 1
                
                # Track products for this category
                if top_category not in category_products:
                    category_products[top_category] = []
                category_products[top_category].append(claim['product_name'])
        
        # Format results
        results = []
        for category, count in category_counts.most_common():
            results.append({
                'category': category,
                'count': count,
                'percentage': round((count / len(claims_data)) * 100, 1) if claims_data else 0,
                'top_products': self._get_top_products(category_products.get(category, []))
            })
        
        return {
            'total_claims_analyzed': len(claims_data),
            'categories': results,
            'ai_powered': True
        }
    
    def analyze_rejection_reasons(self, rejected_claims_data: List[Dict]) -> Dict[str, Any]:
        """
        Analyze rejection notes to understand why claims are being rejected
        """
        if not self.client or not rejected_claims_data:
            return self._get_fallback_rejection_analysis(rejected_claims_data)
        
        category_counts = Counter()
        category_examples = {}
        
        for claim in rejected_claims_data:
            # Get all notes for the claim
            notes_text = " ".join(claim.get('notes', []))
            
            if not notes_text:
                continue
            
            # Classify the rejection reason
            scores = self.classify_text(notes_text, self.rejection_categories)
            
            if scores:
                # Get the top category
                top_category = max(scores.items(), key=lambda x: x[1])[0]
                category_counts[top_category] += 1
                
                # Store example
                if top_category not in category_examples:
                    category_examples[top_category] = []
                if len(category_examples[top_category]) < 3:
                    category_examples[top_category].append({
                        'claim_number': claim['claim_number'],
                        'product': claim['product_name']
                    })
        
        # Format results
        results = []
        for category, count in category_counts.most_common():
            results.append({
                'reason': category,
                'count': count,
                'percentage': round((count / len(rejected_claims_data)) * 100, 1) if rejected_claims_data else 0,
                'examples': category_examples.get(category, [])
            })
        
        return {
            'total_rejections_analyzed': len(rejected_claims_data),
            'rejection_reasons': results,
            'ai_powered': True
        }
    
    def generate_insights_summary(self, analytics_data: Dict) -> str:
        """
        Generate a summary of insights using summarization model
        """
        if not self.client:
            return "AI insights unavailable - API key not configured"
        
        try:
            # Create a comprehensive text summary of the data
            text_parts = []
            
            # Top claimed products
            if analytics_data.get('top_claimed_products'):
                products = analytics_data['top_claimed_products'][:3]
                text_parts.append(
                    f"The most claimed products are: " + 
                    ", ".join([f"{p['product_name']} with {p['claim_count']} claims" for p in products])
                )
            
            # Slow processing claims
            if analytics_data.get('slow_processing_claims'):
                slow = analytics_data['slow_processing_claims'][:2]
                text_parts.append(
                    f"Claims taking longest to process: " + 
                    ", ".join([f"{c['product_name']} averaging {c['avg_processing_days']} days" for c in slow])
                )
            
            # Claim reasons
            if analytics_data.get('claim_reasons', {}).get('categories'):
                reasons = analytics_data['claim_reasons']['categories'][:3]
                text_parts.append(
                    f"Main claim reasons: " + 
                    ", ".join([f"{r['category']} ({r['percentage']}%)" for r in reasons])
                )
            
            # Rejection reasons
            if analytics_data.get('rejection_reasons', {}).get('rejection_reasons'):
                rejections = analytics_data['rejection_reasons']['rejection_reasons'][:3]
                text_parts.append(
                    f"Top rejection reasons: " + 
                    ", ".join([f"{r['reason']} ({r['percentage']}%)" for r in rejections])
                )
            
            full_text = ". ".join(text_parts) + "."
            
            # Generate summary
            # Result is a string directly
            summary = self.client.summarization(
                full_text,
                model="facebook/bart-large-cnn"
            )
            
            return summary if isinstance(summary, str) else str(summary)
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Unable to generate AI summary at this time"
    
    def _get_top_products(self, products: List[str], top_n: int = 3) -> List[Dict]:
        """Get top N most common products from list"""
        counter = Counter(products)
        return [
            {'product': product, 'count': count}
            for product, count in counter.most_common(top_n)
        ]
    
    def _get_fallback_claim_analysis(self, claims_data: List[Dict]) -> Dict[str, Any]:
        """
        Fallback analysis when AI is not available
        Uses simple keyword matching
        """
        category_counts = Counter()
        
        keyword_map = {
            'Battery issue': ['battery', 'charging', 'power', 'drain'],
            'Screen damage': ['screen', 'display', 'crack', 'broken', 'shatter'],
            'Hardware malfunction': ['hardware', 'button', 'port', 'camera', 'speaker'],
            'Software problem': ['software', 'freeze', 'crash', 'app', 'update', 'bug'],
            'Water damage': ['water', 'liquid', 'wet', 'moisture'],
            'Overheating': ['heat', 'hot', 'overheat', 'temperature'],
            'Physical damage': ['drop', 'damage', 'dent', 'scratch', 'physical'],
        }
        
        for claim in claims_data:
            text = f"{claim['issue_summary']} {claim['detailed_description']}".lower()
            
            matched = False
            for category, keywords in keyword_map.items():
                if any(keyword in text for keyword in keywords):
                    category_counts[category] += 1
                    matched = True
                    break
            
            if not matched:
                category_counts['Other'] += 1
        
        results = []
        for category, count in category_counts.most_common():
            results.append({
                'category': category,
                'count': count,
                'percentage': round((count / len(claims_data)) * 100, 1) if claims_data else 0
            })
        
        return {
            'total_claims_analyzed': len(claims_data),
            'categories': results,
            'ai_powered': False,
            'note': 'Using keyword-based analysis (AI unavailable)'
        }
    
    def _get_fallback_rejection_analysis(self, rejected_claims_data: List[Dict]) -> Dict[str, Any]:
        """
        Fallback rejection analysis when AI is not available
        """
        category_counts = Counter()
        
        keyword_map = {
            'Physical damage not covered': ['physical damage', 'not covered', 'accidental'],
            'Warranty expired': ['expired', 'expiry', 'warranty period'],
            'Misuse or abuse': ['misuse', 'abuse', 'improper'],
            'Missing documentation': ['documentation', 'proof', 'missing', 'evidence'],
            'Unauthorized repairs': ['unauthorized', 'third party', 'repair'],
        }
        
        for claim in rejected_claims_data:
            notes_text = " ".join(claim.get('notes', [])).lower()
            
            if not notes_text:
                category_counts['Other'] += 1
                continue
            
            matched = False
            for category, keywords in keyword_map.items():
                if any(keyword in notes_text for keyword in keywords):
                    category_counts[category] += 1
                    matched = True
                    break
            
            if not matched:
                category_counts['Other'] += 1
        
        results = []
        for category, count in category_counts.most_common():
            results.append({
                'reason': category,
                'count': count,
                'percentage': round((count / len(rejected_claims_data)) * 100, 1) if rejected_claims_data else 0
            })
        
        return {
            'total_rejections_analyzed': len(rejected_claims_data),
            'rejection_reasons': results,
            'ai_powered': False,
            'note': 'Using keyword-based analysis (AI unavailable)'
        }

