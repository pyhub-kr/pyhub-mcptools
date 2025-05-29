"""Korean sentiment analyzer using dictionary-based approach."""

import json
import os
from typing import Dict, List, Tuple
from pathlib import Path
from .base import BaseSentimentAnalyzer


class KoreanSentimentAnalyzer(BaseSentimentAnalyzer):
    """Korean sentiment analyzer using dictionary approach."""

    def __init__(self):
        """Initialize Korean sentiment analyzer."""
        self.data_dir = Path(__file__).parent.parent / "data"
        self.positive_words = self._load_dict("korean_positive.json")
        self.negative_words = self._load_dict("korean_negative.json")
        self.modifiers = self._load_dict("korean_modifiers.json")

    def _load_dict(self, filename: str) -> Dict[str, float]:
        """Load dictionary from JSON file."""
        filepath = self.data_dir / filename
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def analyze(self, text: str) -> Dict[str, any]:
        """Analyze sentiment of Korean text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment analysis results
        """
        # Tokenize (simple space-based)
        tokens = text.split()

        # Calculate scores
        pos_score = 0.0
        neg_score = 0.0
        pos_keywords = []
        neg_keywords = []

        for i, token in enumerate(tokens):
            # Check for sentiment words
            pos_value, pos_word = self._check_sentiment_word(token, self.positive_words)
            neg_value, neg_word = self._check_sentiment_word(token, self.negative_words)

            # Apply modifier if previous token is a modifier
            modifier = 1.0
            if i > 0:
                prev_token = tokens[i - 1]
                if prev_token in self.modifiers:
                    modifier = self.modifiers[prev_token]
                    # If modifier is negative, swap scores
                    if modifier < 0:
                        pos_value, neg_value = neg_value * abs(modifier), pos_value * abs(modifier)
                        modifier = 1.0

            # Add to scores
            if pos_value > 0:
                pos_score += pos_value * modifier
                if pos_word:
                    pos_keywords.append(pos_word)
            if neg_value > 0:
                neg_score += neg_value * modifier
                if neg_word:
                    neg_keywords.append(neg_word)

        # Neutral score (base level)
        if pos_score == 0 and neg_score == 0:
            neu_score = 1.0
        else:
            neu_score = max(0.1, 1.0 - (pos_score + neg_score))

        # Classify sentiment
        sentiment, confidence = self.classify_sentiment(pos_score, neg_score, neu_score)

        # Adjust confidence for neutral sentiment
        if sentiment == "neutral" and pos_score == 0 and neg_score == 0:
            confidence = 0.5  # Lower confidence when no sentiment words found

        # Combine keywords
        keywords = pos_keywords if sentiment == "positive" else neg_keywords

        return {
            "sentiment": sentiment,
            "confidence": min(confidence, 0.99),  # Cap at 0.99
            "scores": {
                "positive": pos_score / (pos_score + neg_score + neu_score),
                "negative": neg_score / (pos_score + neg_score + neu_score),
                "neutral": neu_score / (pos_score + neg_score + neu_score),
            },
            "keywords": list(set(keywords))[:5],  # Unique top 5
        }

    def _check_sentiment_word(self, token: str, word_dict: Dict[str, float]) -> Tuple[float, str]:
        """Check if token contains any sentiment word.

        Args:
            token: Token to check
            word_dict: Dictionary of sentiment words

        Returns:
            Tuple of (score, matched_word)
        """
        # Check exact match first
        if token in word_dict:
            return word_dict[token], token

        # Check if token contains any sentiment word
        for word, score in word_dict.items():
            if word in token:
                return score, word

        return 0.0, None
