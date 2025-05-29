"""English sentiment analyzer using VADER."""

from typing import Dict, List

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

from .base import BaseSentimentAnalyzer


class EnglishSentimentAnalyzer(BaseSentimentAnalyzer):
    """English sentiment analyzer using VADER."""

    def __init__(self):
        """Initialize VADER analyzer."""
        if not VADER_AVAILABLE:
            raise ImportError("VADER sentiment analyzer is not available. Install with: pip install vaderSentiment")
        self.analyzer = SentimentIntensityAnalyzer()

    def analyze(self, text: str) -> Dict[str, any]:
        """Analyze sentiment of English text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment analysis results
        """
        # Get VADER scores
        scores = self.analyzer.polarity_scores(text)

        # Extract individual scores
        pos_score = scores["pos"]
        neg_score = scores["neg"]
        neu_score = scores["neu"]
        compound = scores["compound"]

        # Classify sentiment based on compound score
        if compound >= 0.05:
            sentiment = "positive"
        elif compound <= -0.05:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        # Calculate confidence
        confidence = abs(compound)

        # Extract keywords (VADER doesn't provide this, so we'll do basic extraction)
        keywords = self._extract_keywords(text, sentiment)

        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "scores": {"positive": pos_score, "negative": neg_score, "neutral": neu_score, "compound": compound},
            "keywords": keywords,
        }

    def _extract_keywords(self, text: str, sentiment: str) -> List[str]:
        """Extract keywords based on sentiment.

        Simple keyword extraction based on common sentiment words.
        """
        text_lower = text.lower()
        keywords = []

        # Common positive words
        positive_words = [
            "good",
            "great",
            "excellent",
            "amazing",
            "wonderful",
            "fantastic",
            "love",
            "best",
            "happy",
            "beautiful",
            "perfect",
            "awesome",
        ]

        # Common negative words
        negative_words = [
            "bad",
            "terrible",
            "awful",
            "horrible",
            "worst",
            "hate",
            "ugly",
            "disgusting",
            "poor",
            "disappointing",
            "useless",
            "waste",
        ]

        if sentiment == "positive":
            keywords = [word for word in positive_words if word in text_lower]
        elif sentiment == "negative":
            keywords = [word for word in negative_words if word in text_lower]

        return keywords[:5]  # Return top 5 keywords
