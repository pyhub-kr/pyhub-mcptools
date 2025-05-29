"""Base sentiment analyzer class."""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


class BaseSentimentAnalyzer(ABC):
    """Base class for sentiment analyzers."""

    @abstractmethod
    def analyze(self, text: str) -> Dict[str, any]:
        """Analyze sentiment of text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment analysis results:
            - sentiment: 'positive', 'negative', or 'neutral'
            - confidence: float between 0 and 1
            - scores: dict with positive, negative, neutral scores
            - keywords: list of key sentiment words found
        """
        pass

    def classify_sentiment(self, pos_score: float, neg_score: float, neu_score: float) -> Tuple[str, float]:
        """Classify sentiment based on scores.

        Args:
            pos_score: Positive score
            neg_score: Negative score
            neu_score: Neutral score

        Returns:
            Tuple of (sentiment, confidence)
        """
        total = pos_score + neg_score + neu_score
        if total == 0:
            return "neutral", 0.0

        # Normalize scores
        pos_norm = pos_score / total
        neg_norm = neg_score / total
        neu_norm = neu_score / total

        # Determine sentiment
        if pos_norm > neg_norm and pos_norm > neu_norm:
            sentiment = "positive"
            confidence = pos_norm
        elif neg_norm > pos_norm and neg_norm > neu_norm:
            sentiment = "negative"
            confidence = neg_norm
        else:
            sentiment = "neutral"
            confidence = neu_norm

        return sentiment, confidence
