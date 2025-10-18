"""
Test script for AI-powered analytics endpoint
Run this after installing dependencies and starting the server
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if your server runs on a different port
API_ENDPOINT = f"{BASE_URL}/api/analytics/ai-insights/"

# You'll need to replace this with a valid JWT token from a retailer or admin account
# To get a token, first login via /api/accounts/login/
AUTH_TOKEN = "your_jwt_token_here"

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}


def test_ai_insights(period='6months'):
    """
    Test the AI insights endpoint
    
    Args:
        period: One of '30days', '90days', '6months', '12months', 'all'
    """
    print(f"\n{'='*80}")
    print(f"Testing AI Insights Endpoint - Period: {period}")
    print(f"{'='*80}\n")
    
    try:
        response = requests.get(
            API_ENDPOINT,
            headers=headers,
            params={'period': period}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n✅ SUCCESS! Here's the response structure:\n")
            
            # Overall Statistics
            print("📊 OVERALL STATISTICS:")
            stats = data.get('overall_statistics', {})
            print(f"  • Total Claims: {stats.get('total_claims')}")
            print(f"  • Approved: {stats.get('approved_claims')}")
            print(f"  • Rejected: {stats.get('rejected_claims')}")
            print(f"  • Pending: {stats.get('pending_claims')}")
            print(f"  • Approval Rate: {stats.get('approval_rate')}%")
            print(f"  • Rejection Rate: {stats.get('rejection_rate')}%")
            
            # Top Claimed Products
            print("\n🏆 TOP CLAIMED PRODUCTS:")
            products = data.get('top_claimed_products', [])
            for i, product in enumerate(products[:5], 1):
                print(f"  {i}. {product['product_name']} ({product['model']})")
                print(f"     Claims: {product['claim_count']} | Approval Rate: {product['approval_rate']}%")
            
            # Slow Processing Claims
            print("\n⏱️  SLOW PROCESSING CLAIMS:")
            slow = data.get('slow_processing_claims', [])
            for i, item in enumerate(slow[:5], 1):
                print(f"  {i}. {item['product_name']} - Avg: {item['avg_processing_days']} days")
            
            # Claim Reasons (AI Analysis)
            print("\n🤖 AI ANALYSIS - CLAIM REASONS:")
            reasons = data.get('claim_reasons', {})
            print(f"  AI Powered: {reasons.get('ai_powered', False)}")
            categories = reasons.get('categories', [])
            for i, cat in enumerate(categories[:5], 1):
                print(f"  {i}. {cat['category']}: {cat['count']} ({cat['percentage']}%)")
            
            # Rejection Reasons (AI Analysis)
            print("\n🤖 AI ANALYSIS - REJECTION REASONS:")
            rejections = data.get('rejection_reasons', {})
            print(f"  AI Powered: {rejections.get('ai_powered', False)}")
            rej_reasons = rejections.get('rejection_reasons', [])
            for i, reason in enumerate(rej_reasons[:5], 1):
                print(f"  {i}. {reason['reason']}: {reason['count']} ({reason['percentage']}%)")
            
            # AI Summary
            print("\n💡 AI SUMMARY:")
            summary = data.get('ai_summary', 'N/A')
            print(f"  {summary}")
            
            # Recommendations
            print("\n📋 RECOMMENDATIONS:")
            recs = data.get('recommendations', [])
            for i, rec in enumerate(recs, 1):
                print(f"  {i}. [{rec['priority'].upper()}] {rec['title']}")
                print(f"     {rec['description']}")
                print(f"     Action: {rec['action']}")
            
            # Save full response to file
            with open('ai_insights_response.json', 'w') as f:
                json.dump(data, f, indent=2)
            print("\n📁 Full response saved to: ai_insights_response.json")
            
        elif response.status_code == 403:
            print("❌ ERROR: Access forbidden. This endpoint is only for retailers and admins.")
        elif response.status_code == 401:
            print("❌ ERROR: Unauthorized. Please provide a valid JWT token.")
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to server. Make sure the Django server is running.")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")


def test_all_periods():
    """Test all available periods"""
    periods = ['30days', '90days', '6months', '12months', 'all']
    
    for period in periods:
        test_ai_insights(period)
        print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    print("\n🚀 AI Analytics Endpoint Test Script")
    print("="*80)
    
    if AUTH_TOKEN == "your_jwt_token_here":
        print("\n⚠️  WARNING: You need to set a valid JWT token in this script!")
        print("Steps to get a token:")
        print("1. Start the Django server: python manage.py runserver")
        print("2. Login via: POST http://localhost:8000/api/accounts/login/")
        print("3. Copy the 'access' token from the response")
        print("4. Replace 'your_jwt_token_here' in this script with your token")
        print("\nExample login request:")
        print("""
curl -X POST http://localhost:8000/api/accounts/login/ \\
  -H "Content-Type: application/json" \\
  -d '{"email": "retailer@example.com", "password": "your_password"}'
        """)
    else:
        # Test with default period
        test_ai_insights('6months')
        
        # Uncomment to test all periods
        # test_all_periods()

