"""
Test Hugging Face API directly
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings
from huggingface_hub import InferenceClient

print("="*60)
print("Testing Hugging Face API")
print("="*60)

# Get API key
api_key = settings.HUGGINGFACE_API_KEY
print(f"\nAPI Key configured: {bool(api_key)}")
if api_key:
    print(f"API Key starts with: {api_key[:10]}...")

# Initialize client
try:
    client = InferenceClient(token=api_key, timeout=30)
    print("\n[OK] Client initialized successfully")
except Exception as e:
    print(f"\n[ERROR] Client initialization failed: {e}")
    exit(1)

# Test zero-shot classification
print("\n" + "="*60)
print("Testing Zero-Shot Classification")
print("="*60)

test_text = "My phone battery drains very quickly"
categories = ["Battery issue", "Screen damage", "Water damage"]

try:
    result = client.zero_shot_classification(
        text=test_text,
        labels=categories,
        model="facebook/bart-large-mnli"
    )
    print(f"\n[OK] Classification successful!")
    print(f"Text: {test_text}")
    print(f"\nResults:")
    for label, score in zip(result.labels, result.scores):
        print(f"  {label}: {score:.4f}")
except Exception as e:
    print(f"\n[ERROR] Classification failed: {e}")
    import traceback
    traceback.print_exc()

# Test summarization
print("\n" + "="*60)
print("Testing Summarization")
print("="*60)

test_text_long = """
The most claimed products are iPhone 14 Pro with 25 claims and Samsung Galaxy S23 with 12 claims. 
Claims taking longest to process include iPhone 14 Pro averaging 8.5 days. 
Main claim reasons include Battery issues at 30% and Screen damage at 25%.
Top rejection reasons are Physical damage not covered at 37%.
"""

try:
    result = client.summarization(
        test_text_long,
        model="facebook/bart-large-cnn"
    )
    print(f"\n[OK] Summarization successful!")
    print(f"\nOriginal length: {len(test_text_long)} chars")
    print(f"Summary: {result}")
except Exception as e:
    print(f"\n[ERROR] Summarization failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("All tests completed!")
print("="*60)

