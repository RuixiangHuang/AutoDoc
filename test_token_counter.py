#!/usr/bin/env python3
"""
Test script for token counter functionality
"""
from token_counter import TokenCounter, get_token_counter

def test_token_counter():
    """Test basic token counter functionality"""
    print("=" * 60)
    print("Testing Token Counter")
    print("=" * 60)
    
    # Create a new counter
    counter = TokenCounter()
    
    # Test 1: Basic counting
    print("\n[Test 1] Adding usage data...")
    counter.add_usage(100, 50, "groq_llama-3.3-70b-versatile", "explanation")
    counter.add_usage(150, 75, "groq_llama-3.3-70b-versatile", "explanation")
    counter.add_usage(200, 100, "groq_llama-3.3-70b-versatile", "explanation")
    
    summary = counter.get_summary("groq_llama-3.3-70b-versatile")
    print(f"Total calls: {summary['total_calls']}")
    print(f"Total input tokens: {summary['total_input_tokens']}")
    print(f"Total output tokens: {summary['total_output_tokens']}")
    print(f"Total tokens: {summary['total_tokens']}")
    print(f"Estimated cost: ${summary['estimated_cost_usd']:.4f}")
    
    assert summary['total_calls'] == 3, "Should have 3 calls"
    assert summary['total_input_tokens'] == 450, "Should have 450 input tokens"
    assert summary['total_output_tokens'] == 225, "Should have 225 output tokens"
    print("✅ Test 1 passed!")
    
    # Test 2: Token estimation
    print("\n[Test 2] Testing token estimation...")
    test_text = "This is a test string for token counting."
    estimated = counter.estimate_tokens(test_text)
    print(f"Text: '{test_text}'")
    print(f"Estimated tokens: {estimated}")
    assert estimated > 0, "Should estimate some tokens"
    print("✅ Test 2 passed!")
    
    # Test 3: Cost calculation for Ollama (free)
    print("\n[Test 3] Testing Ollama (free) cost...")
    counter.reset()
    counter.add_usage(1000, 500, "ollama", "explanation")
    summary = counter.get_summary("ollama")
    print(f"Total tokens: {summary['total_tokens']}")
    print(f"Cost: ${summary['estimated_cost_usd']:.4f}")
    assert summary['estimated_cost_usd'] == 0, "Ollama should be free"
    print("✅ Test 3 passed!")
    
    # Test 4: Format summary
    print("\n[Test 4] Testing formatted summary...")
    counter.reset()
    counter.add_usage(500, 250, "groq_llama-3.3-70b-versatile", "explanation")
    counter.add_usage(600, 300, "groq_llama-3.3-70b-versatile", "explanation")
    formatted = counter.format_summary("groq_llama-3.3-70b-versatile")
    print("\n" + formatted)
    assert "Token Usage Summary" in formatted, "Should contain summary header"
    print("✅ Test 4 passed!")
    
    # Test 5: Global counter
    print("\n[Test 5] Testing global counter...")
    global_counter = get_token_counter()
    global_counter.reset()
    global_counter.add_usage(100, 50, "test_model", "test")
    assert global_counter.total_calls == 1, "Global counter should work"
    print("✅ Test 5 passed!")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✅")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_token_counter()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

