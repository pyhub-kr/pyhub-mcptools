"""Sentiment analysis MCP tools."""

import asyncio
import json
from typing import Literal

from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.json_utils import json_dumps
from .analyzers import EnglishSentimentAnalyzer, KoreanSentimentAnalyzer


# Initialize analyzers
english_analyzer = None
korean_analyzer = None


def get_english_analyzer():
    """Get or create English analyzer."""
    global english_analyzer
    if english_analyzer is None:
        try:
            english_analyzer = EnglishSentimentAnalyzer()
        except ImportError:
            return None
    return english_analyzer


def get_korean_analyzer():
    """Get or create Korean analyzer."""
    global korean_analyzer
    if korean_analyzer is None:
        korean_analyzer = KoreanSentimentAnalyzer()
    return korean_analyzer


def detect_language(text: str) -> str:
    """Simple language detection based on character ranges."""
    # Count Korean characters
    korean_chars = sum(1 for char in text if "\uac00" <= char <= "\ud7a3")
    # Count English characters
    english_chars = sum(1 for char in text if "a" <= char.lower() <= "z")

    if korean_chars > english_chars:
        return "ko"
    elif english_chars > 0:
        return "en"
    else:
        return "unknown"


@mcp.tool(timeout=30)
async def sentiment_analyze(
    text: str | list[str] = Field(
        description="Text or list of texts to analyze for sentiment",
        examples=[
            "This product is amazing! I love it.",
            "정말 좋아요! 최고입니다",
            ["Good product", "Bad service", "It's okay"],
            ["좋아요", "별로예요", "그저 그래요"],
        ],
    ),
    language: Literal["auto", "en", "ko"] = Field(
        default="auto", description="Language of the text (auto-detect by default)"
    ),
) -> str:
    """Analyze sentiment of text(s) (positive/negative/neutral).

    This tool analyzes the sentiment of given text without using LLMs.
    It uses dictionary-based approach for Korean and VADER for English.

    Supports both single text and batch processing:
    - Single text: Returns sentiment analysis result
    - List of texts: Returns list of results

    Features:
    - Supports English and Korean
    - Returns sentiment (positive/negative/neutral)
    - Provides confidence score
    - Extracts key sentiment words
    - Handles negation and modifiers

    Returns:
        JSON string with:
        For single text:
        - sentiment: 'positive', 'negative', or 'neutral'
        - confidence: float between 0 and 1
        - scores: detailed scores for each sentiment
        - keywords: key sentiment words found
        - language: detected or specified language

        For multiple texts:
        - List of results, each containing above fields plus 'text'
    """
    # Handle batch processing
    if isinstance(text, list):
        results = []
        for single_text in text:
            # Analyze each text
            result = await _analyze_single_text(single_text, language)
            result["text"] = single_text
            results.append(result)
        return json_dumps(results)

    # Single text processing
    result = await _analyze_single_text(text, language)
    return json_dumps(result)


async def _analyze_single_text(text: str, language: str) -> dict:
    """Analyze a single text."""
    # Detect language if auto
    if language == "auto":
        detected_lang = detect_language(text)
        language = detected_lang if detected_lang != "unknown" else "en"

    # Get appropriate analyzer
    if language == "ko":
        analyzer = get_korean_analyzer()
    else:
        analyzer = get_english_analyzer()
        if analyzer is None:
            # Fallback to Korean analyzer if VADER not available
            analyzer = get_korean_analyzer()
            language = "ko"

    # Analyze sentiment
    result = await asyncio.to_thread(analyzer.analyze, text)
    result["language"] = language

    return result
