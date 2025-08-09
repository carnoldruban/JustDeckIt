from collections import deque

# Define card categories
HIGH_CARDS = ['10', 'J', 'Q', 'K', 'A']
LOW_CARDS = ['2', '3', '4', '5', '6']
MIDDLE_CARDS = ['7', '8', '9']

class SequencePredictor:
    """
    Analyzes a sequence of played cards to predict the category of the next card.
    """
    def __init__(self, history_size=100, trend_size=15):
        self.history_size = history_size
        self.trend_size = trend_size
        self.seen_cards = deque(maxlen=history_size)

    def _get_card_category(self, card_rank: str) -> str:
        """Determines if a card is High, Middle, or Low."""
        if card_rank in HIGH_CARDS:
            return "High"
        if card_rank in LOW_CARDS:
            return "Low"
        if card_rank in MIDDLE_CARDS:
            return "Middle"
        return "Unknown"

    def track_card(self, card_rank: str):
        """Adds a new card to the history."""
        category = self._get_card_category(card_rank)
        if category != "Unknown":
            self.seen_cards.append(category)

    def get_prediction(self) -> str:
        """
        Analyzes the card history and predicts the next card's category.
        """
        if len(self.seen_cards) < self.history_size:
            return f"Analyzing... ({len(self.seen_cards)}/{self.history_size})"

        # --- Algorithm ---
        # 1. Frequency Analysis on the last 100 cards
        history = list(self.seen_cards)
        freq_high = history.count("High")
        freq_middle = history.count("Middle")
        freq_low = history.count("Low")

        # 2. Trend Analysis on the last 15 cards
        trend_history = history[-self.trend_size:]
        trend_high = trend_history.count("High")
        trend_middle = trend_history.count("Middle")
        trend_low = trend_history.count("Low")

        # 3. Scoring Logic
        # Base score is the frequency over the last 100 cards.
        # Add a bonus for recent trends.
        score_high = freq_high + (trend_high * 1.5) # Bonus for recent high cards
        score_middle = freq_middle + (trend_middle * 1.2) # Smaller bonus for middle cards
        score_low = freq_low + (trend_low * 1.5) # Bonus for recent low cards

        # 4. Prediction
        scores = {
            "High": score_high,
            "Middle": score_middle,
            "Low": score_low
        }

        # Find the category with the highest score
        prediction = max(scores, key=scores.get)

        return f"Prediction: {prediction} Card"

    def reset(self):
        """Resets the card history."""
        self.seen_cards.clear()
        print("[Predictor] History cleared.")

if __name__ == '__main__':
    predictor = SequencePredictor(history_size=20, trend_size=5) # Smaller sizes for testing

    print("--- Testing Sequence Predictor ---")
    print(predictor.get_prediction()) # Should show "Analyzing..."

    # Simulate some cards
    test_cards = ['2','3','K','4','A','5','J','6','Q','2','3','K','4','A','5','J','6','Q','2','3']
    for rank in test_cards:
        predictor.track_card(rank)

    print(f"\nAfter {len(test_cards)} cards:")
    print(predictor.get_prediction()) # Should now make a prediction

    # Simulate a run of high cards
    for _ in range(5):
        predictor.track_card('K')

    print("\nAfter a run of 5 Kings:")
    print(predictor.get_prediction()) # Prediction should likely be "High"

    predictor.reset()
    print(f"\nAfter reset: {predictor.get_prediction()}")
