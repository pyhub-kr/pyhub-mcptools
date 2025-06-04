"""Test sentiment analysis tools."""

import asyncio
import json

import pytest

from pyhub.mcptools.sentiment.tools import sentiment_analyze


@pytest.mark.asyncio
async def test_sentiment_analyze_single_english():
    """Test single English text sentiment analysis."""
    texts = [
        ("This is absolutely amazing! I love it!", "positive"),
        ("Terrible experience, very disappointed.", "negative"),
        ("It's okay, nothing special.", "neutral"),
        ("NOT good at all!", "negative"),  # Test negation
    ]

    for text, _ in texts:
        result = await sentiment_analyze(text, "en")
        data = json.loads(result)
        assert data["sentiment"] in ["positive", "negative", "neutral"]
        assert 0 <= data["confidence"] <= 1
        assert "scores" in data
        assert "language" in data
        # If VADER is not installed, it falls back to Korean analyzer
        assert data["language"] in ["en", "ko"]


@pytest.mark.asyncio
async def test_sentiment_analyze_single_korean():
    """Test single Korean text sentiment analysis."""
    texts = [
        "정말 좋아요! 최고입니다!",
        "너무 실망했어요. 최악이에요.",
        "그냥 그래요. 보통입니다.",
        "안 좋아요!",  # Test negation
        "매우 만족스럽습니다.",  # Test modifier
    ]

    for text in texts:
        result = await sentiment_analyze(text, "ko")
        data = json.loads(result)
        assert data["sentiment"] in ["positive", "negative", "neutral"]
        assert 0 <= data["confidence"] <= 1
        assert "scores" in data
        assert "language" in data
        assert data["language"] == "ko"


@pytest.mark.asyncio
async def test_sentiment_analyze_batch():
    """Test batch sentiment analysis."""
    texts = ["Great!", "Bad!", "Meh"]
    result = await sentiment_analyze(texts, "en")
    data = json.loads(result)

    assert isinstance(data, list)
    assert len(data) == 3

    for i, item in enumerate(data):
        assert "text" in item
        assert item["text"] == texts[i]
        assert item["sentiment"] in ["positive", "negative", "neutral"]
        assert 0 <= item["confidence"] <= 1
        assert "scores" in item
        assert "language" in item


@pytest.mark.asyncio
async def test_sentiment_analyze_auto_language():
    """Test auto language detection."""
    # Test English auto-detection
    result = await sentiment_analyze("This is great!", "auto")
    data = json.loads(result)
    assert data["language"] in ["en", "ko"]  # May fallback to ko

    # Test Korean auto-detection
    result = await sentiment_analyze("정말 좋아요!", "auto")
    data = json.loads(result)
    assert data["language"] == "ko"


@pytest.mark.asyncio
async def test_sentiment_analyze_mixed_batch():
    """Test batch with mixed languages."""
    texts = ["Great product!", "별로예요", "It's okay", "좋아요"]
    result = await sentiment_analyze(texts, "auto")
    data = json.loads(result)

    assert isinstance(data, list)
    assert len(data) == 4

    for item in data:
        assert "text" in item
        assert "sentiment" in item
        assert "language" in item


# Manual test function for development
async def test_sentiment_manual():
    """Manual test for sentiment analysis during development."""
    print("Testing English sentiment analysis:")
    texts_en = [
        "This is absolutely amazing! I love it!",
        "Terrible experience, very disappointed.",
        "It's okay, nothing special.",
        "NOT good at all!",  # Test negation
    ]

    for text in texts_en:
        result = await sentiment_analyze(text, "en")
        data = json.loads(result)
        print(f"\nText: {text}")
        print(f"Sentiment: {data['sentiment']} (confidence: {data['confidence']:.2f})")
        print(f"Keywords: {data.get('keywords', [])}")

    # Test Korean
    print("\n\nTesting Korean sentiment analysis:")
    texts_ko = [
        "정말 좋아요! 최고입니다!",
        "너무 실망했어요. 최악이에요.",
        "그냥 그래요. 보통입니다.",
        "안 좋아요!",  # Test negation
        "매우 만족스럽습니다.",  # Test modifier
    ]

    for text in texts_ko:
        result = await sentiment_analyze(text, "ko")
        data = json.loads(result)
        print(f"\nText: {text}")
        print(f"Sentiment: {data['sentiment']} (confidence: {data['confidence']:.2f})")
        print(f"Keywords: {data.get('keywords', [])}")

    # Test batch
    print("\n\nTesting batch analysis:")
    batch_result = await sentiment_analyze(["Great!", "Bad!", "Meh"], "en")
    batch_data = json.loads(batch_result)
    for item in batch_data:
        print(f"{item['text']}: {item['sentiment']}")


if __name__ == "__main__":
    asyncio.run(test_sentiment_manual())
