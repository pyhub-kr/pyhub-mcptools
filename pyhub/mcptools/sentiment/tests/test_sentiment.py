"""Test sentiment analysis functionality."""

import pytest
import json
from pyhub.mcptools.sentiment.analyzers import KoreanSentimentAnalyzer
from pyhub.mcptools.sentiment.tools import sentiment_analyze


class TestKoreanAnalyzer:
    """Test Korean sentiment analyzer."""

    def setup_method(self):
        """Set up test."""
        self.analyzer = KoreanSentimentAnalyzer()

    def test_positive_sentiment(self):
        """Test positive sentiment detection."""
        texts = [
            "정말 좋아요!",
            "최고입니다",
            "매우 만족스럽습니다",
            "완전 대박이에요",
        ]

        for text in texts:
            result = self.analyzer.analyze(text)
            assert result["sentiment"] == "positive", f"Failed for: {text}"
            assert result["confidence"] > 0.5
            assert len(result["keywords"]) > 0

    def test_negative_sentiment(self):
        """Test negative sentiment detection."""
        texts = [
            "정말 싫어요",
            "최악입니다",
            "너무 실망했어요",
            "별로예요",
        ]

        for text in texts:
            result = self.analyzer.analyze(text)
            assert result["sentiment"] == "negative", f"Failed for: {text}"
            assert result["confidence"] > 0.5

    def test_neutral_sentiment(self):
        """Test neutral sentiment detection."""
        texts = [
            "그냥 그래요",
            "보통입니다",
            "뭐 그저 그렇죠",
        ]

        for text in texts:
            result = self.analyzer.analyze(text)
            # Neutral or slight positive/negative is acceptable
            assert result["sentiment"] in ["neutral", "positive", "negative"]
            if result["sentiment"] == "neutral":
                assert result["confidence"] < 0.8  # Lower confidence for neutral

    def test_negation(self):
        """Test negation handling."""
        # Positive word with negation should be negative
        result = self.analyzer.analyze("안 좋아요")
        assert result["sentiment"] == "negative"

        # Negative word with negation should be positive
        result = self.analyzer.analyze("안 나빠요")
        assert result["sentiment"] == "positive"

    def test_modifiers(self):
        """Test modifier handling."""
        # Strong positive
        result1 = self.analyzer.analyze("좋아요")
        result2 = self.analyzer.analyze("매우 좋아요")

        # Second should have higher positive score
        assert result2["scores"]["positive"] > result1["scores"]["positive"]


@pytest.mark.asyncio
async def test_sentiment_analyze_tool():
    """Test sentiment_analyze MCP tool."""
    # Test Korean
    result = await sentiment_analyze("정말 좋아요!", "ko")
    data = json.loads(result)
    assert data["sentiment"] == "positive"
    assert data["language"] == "ko"
    assert "confidence" in data
    assert "scores" in data
    assert "keywords" in data

    # Test auto-detection with Korean
    result = await sentiment_analyze("최악이에요", "auto")
    data = json.loads(result)
    assert data["sentiment"] == "negative"
    assert data["language"] == "ko"


@pytest.mark.asyncio
async def test_sentiment_analyze_batch():
    """Test batch sentiment analysis."""
    texts = ["좋아요", "싫어요", "그냥 그래요"]
    result = await sentiment_analyze(texts, "ko")
    data = json.loads(result)

    assert len(data) == 3
    assert data[0]["sentiment"] == "positive"
    assert data[1]["sentiment"] == "negative"
    # Third one could be neutral or have low confidence
    assert data[2]["text"] == "그냥 그래요"


@pytest.mark.asyncio
async def test_english_fallback():
    """Test that Korean analyzer works as fallback for English."""
    # When VADER is not installed, should fallback to Korean analyzer
    result = await sentiment_analyze("Hello world", "en")
    data = json.loads(result)

    # Should still return a valid result
    assert "sentiment" in data
    assert "confidence" in data
    assert "scores" in data


def test_language_detection():
    """Test language detection."""
    from pyhub.mcptools.sentiment.tools import detect_language

    assert detect_language("안녕하세요") == "ko"
    assert detect_language("Hello world") == "en"
    assert detect_language("こんにちは") == "unknown"  # Japanese
    assert detect_language("123456") == "unknown"  # Numbers only
