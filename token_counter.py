"""
Token usage counter for LLM calls
Tracks input/output tokens and calculates costs
"""
from typing import Dict, Optional, List
import tiktoken


class TokenCounter:
    """Track token usage across LLM calls"""
    
    def __init__(self):
        self.reset()
        # Approximate cost per 1M tokens (USD)
        self.costs = {
            # Custom Groq models
            "groq_openai/gpt-oss-120b": {"input": 0.59, "output": 0.79},
            "groq_qwen/qwen3-32b": {"input": 0.30, "output": 0.30},
            "groq_meta-llama/llama-4-maverick-17b-128e-instruct": {"input": 0.20, "output": 0.20},
            # Legacy models (kept for backward compatibility)
            "groq_llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
            "groq_llama-3.1-70b-versatile": {"input": 0.59, "output": 0.79},
            "groq_llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
            "groq_mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
            "groq_gemma2-9b-it": {"input": 0.20, "output": 0.20},
            "groq_gemma-7b-it": {"input": 0.07, "output": 0.07},
            "ollama": {"input": 0.0, "output": 0.0},  # Local, free
        }
    
    def reset(self):
        """Reset all counters"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_calls = 0
        self.call_history = []
    
    def add_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "unknown",
        call_type: str = "explanation"
    ):
        """
        Add token usage from a single LLM call
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name
            call_type: Type of call (e.g., "explanation", "query")
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_calls += 1
        
        self.call_history.append({
            "call_number": self.total_calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model": model,
            "type": call_type
        })
    
    def estimate_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Estimate token count for text (used for Ollama which doesn't report tokens)
        
        Args:
            text: Text to count tokens for
            model: Model name for encoding
        
        Returns:
            Estimated token count
        """
        try:
            encoding = tiktoken.encoding_for_model(model)
        except:
            # Fallback to cl100k_base if model not found
            encoding = tiktoken.get_encoding("cl100k_base")
        
        return len(encoding.encode(text))
    
    def calculate_cost(self, model_key: str = "ollama") -> Dict[str, float]:
        """
        Calculate estimated cost based on token usage
        
        Args:
            model_key: Key for cost lookup (e.g., "groq_llama-3.3-70b-versatile")
        
        Returns:
            Dict with input_cost, output_cost, total_cost
        """
        if model_key not in self.costs:
            # Try to find a matching key
            for key in self.costs.keys():
                if model_key in key or key in model_key:
                    model_key = key
                    break
            else:
                model_key = "ollama"
        
        cost_config = self.costs[model_key]
        
        input_cost = (self.total_input_tokens / 1_000_000) * cost_config["input"]
        output_cost = (self.total_output_tokens / 1_000_000) * cost_config["output"]
        
        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost
        }
    
    def get_summary(self, model_key: str = "ollama") -> Dict:
        """
        Get complete usage summary
        
        Returns:
            Dict with all statistics
        """
        costs = self.calculate_cost(model_key)
        
        return {
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "avg_input_tokens": self.total_input_tokens / max(self.total_calls, 1),
            "avg_output_tokens": self.total_output_tokens / max(self.total_calls, 1),
            "estimated_cost_usd": costs["total_cost"],
            "input_cost_usd": costs["input_cost"],
            "output_cost_usd": costs["output_cost"]
        }
    
    def format_summary(self, model_key: str = "ollama") -> str:
        """Format summary as readable string"""
        summary = self.get_summary(model_key)
        
        lines = [
            "=" * 50,
            "Token Usage Summary",
            "=" * 50,
            f"Total LLM Calls: {summary['total_calls']}",
            f"Input Tokens:    {summary['total_input_tokens']:,}",
            f"Output Tokens:   {summary['total_output_tokens']:,}",
            f"Total Tokens:    {summary['total_tokens']:,}",
            "",
            f"Avg Input/Call:  {summary['avg_input_tokens']:.0f}",
            f"Avg Output/Call: {summary['avg_output_tokens']:.0f}",
        ]
        
        if summary['estimated_cost_usd'] > 0:
            lines.extend([
                "",
                "Estimated Cost (USD):",
                f"  Input:  ${summary['input_cost_usd']:.4f}",
                f"  Output: ${summary['output_cost_usd']:.4f}",
                f"  Total:  ${summary['estimated_cost_usd']:.4f}",
            ])
        else:
            lines.append("\nCost: $0.00 (Local model)")
        
        lines.append("=" * 50)
        
        return "\n".join(lines)


# Global counter instance
_global_counter = TokenCounter()


def get_token_counter() -> TokenCounter:
    """Get global token counter instance"""
    return _global_counter

