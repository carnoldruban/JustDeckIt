class CardCounter:
    def __init__(self, num_decks=8):
        self.num_decks = num_decks
        self.reset()

    def reset(self):
        self.running_count = 0
        self.seen_cards = []
        self.card_values = {
            '2': 1, '3': 1, '4': 1, '5': 1, '6': 1,
            '7': 0, '8': 0, '9': 0,
            'T': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
        }

    def process_cards(self, cards: list[str]):
        """Processes a list of card strings (e.g., 'KH', 'AS')."""
        for card_str in cards:
            rank = card_str[0].upper()
            if rank in self.card_values:
                self.running_count += self.card_values[rank]
                self.seen_cards.append(card_str)

    def get_running_count(self) -> int:
        return self.running_count

    def get_decks_remaining(self) -> float:
        total_cards = self.num_decks * 52
        cards_left = total_cards - len(self.seen_cards)
        return max(0.5, cards_left / 52)

    def get_true_count(self) -> float:
        decks_remaining = self.get_decks_remaining()
        if decks_remaining == 0:
            return 0
        return self.running_count / decks_remaining
