"""Token estimation utilities for ChatGPT context."""
from typing import Final

# Common LLM context limits (in tokens)
# Using Cursor's 200k as the base comparison
CURSOR_CONTEXT: Final[int] = 200_000
GPT_5_CONTEXT: Final[int] = 400_000
CLAUDE_OPUS_4_5_CONTEXT: Final[int] = 200_000
GEMINI_3_PRO_CONTEXT: Final[int] = 10_000_000
GPT_4_1_CONTEXT: Final[int] = 1_000_000

# Average characters per token for code (rough estimate)
# Code typically has 3-4 chars per token, we'll use 3.5 as a middle ground
CHARS_PER_TOKEN: Final[float] = 3.5


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    Uses a simple character-based approximation suitable for code.
    """
    if not text:
        return 0
    # Rough approximation: code typically has 3-4 characters per token
    return int(len(text) / CHARS_PER_TOKEN)


def format_percentage(value: float) -> str:
    """Format percentage with appropriate precision."""
    if value < 0.1:
        return f"{value:.2f}%"
    elif value < 1:
        return f"{value:.1f}%"
    elif value < 10:
        return f"{value:.1f}%"
    else:
        return f"{value:.0f}%"


def format_token_info(text: str) -> str:
    """
    Format token information for display.
    Returns a formatted string with tokens, characters, and context usage for multiple models.
    """
    tokens = estimate_tokens(text)
    chars = len(text)
    
    # Calculate context usage percentages
    cursor_pct = (tokens / CURSOR_CONTEXT) * 100
    gpt5_pct = (tokens / GPT_5_CONTEXT) * 100
    gemini_pct = (tokens / GEMINI_3_PRO_CONTEXT) * 100
    gpt41_pct = (tokens / GPT_4_1_CONTEXT) * 100
    
    # Format the main info
    token_str = f"{tokens:,} tokens ({chars:,} chars)"
    
    # Add context percentages - show Cursor first (base), then others
    context_info = f"Cursor: {format_percentage(cursor_pct)}, GPT-5: {format_percentage(gpt5_pct)}, Gemini 3 Pro: {format_percentage(gemini_pct)}, GPT-4.1: {format_percentage(gpt41_pct)}"
    
    return f"{token_str} - {context_info}"


def get_context_usage(text: str) -> dict[str, int | float]:
    """
    Get detailed context usage information for all models.
    Returns a dictionary with token count, character count, and percentages for each model.
    """
    tokens = estimate_tokens(text)
    chars = len(text)
    
    return {
        "tokens": tokens,
        "characters": chars,
        "cursor_percent": (tokens / CURSOR_CONTEXT) * 100,
        "gpt5_percent": (tokens / GPT_5_CONTEXT) * 100,
        "claude_opus_4_5_percent": (tokens / CLAUDE_OPUS_4_5_CONTEXT) * 100,
        "gemini_3_pro_percent": (tokens / GEMINI_3_PRO_CONTEXT) * 100,
        "gpt_4_1_percent": (tokens / GPT_4_1_CONTEXT) * 100,
    }
