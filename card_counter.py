import math

class CardCounter:
    def __init__(self, num_decks=8):
        self.num_decks = num_decks
        self.total_cards = num_decks * 52
        self.running_count = 0
        self.seen_cards = set()

        self.hi_lo_map = {
            '2': 1, '3': 1, '4': 1, '5': 1, '6': 1,
            '7': 0, '8': 0, '9': 0,
            'T': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
        }

    def _get_card_value(self, card_str):
        """Gets the Hi-Lo value of a single card string (e.g., 'KH', '7D')."""
        if not isinstance(card_str, str) or len(card_str) < 1:
            return 0

        rank = card_str[0].upper()
        return self.hi_lo_map.get(rank, 0)

    def process_cards(self, card_list):
        """
        Processes a list of newly seen cards, updating the running count.
        Returns True if the count changed, False otherwise.
        """
        new_cards_found = False
        for card in card_list:
            # Ignore placeholder for unseen cards
            if card == "**":
                continue

            if card not in self.seen_cards:
                self.seen_cards.add(card)
                self.running_count += self._get_card_value(card)
                new_cards_found = True

        return new_cards_found

    def get_running_count(self):
        """Returns the current running count."""
        return self.running_count

    def get_true_count(self):
        """
        Calculates and returns the true count.
        """
        cards_seen = len(self.seen_cards)
        decks_remaining = (self.total_cards - cards_seen) / 52.0

        if decks_remaining <= 0:
            return float('inf') # Or handle as an edge case

        return self.running_count / decks_remaining

    def get_decks_remaining(self):
        """Returns the estimated number of decks remaining."""
        cards_seen = len(self.seen_cards)
        return (self.total_cards - cards_seen) / 52.0

    def reset(self):
        """Resets the counter for a new shoe."""
        self.running_count = 0
        self.seen_cards.clear()
