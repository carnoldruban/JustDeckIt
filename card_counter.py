import math

# Define card values for different counting systems
HI_LO_VALUES = {'2': 1, '3': 1, '4': 1, '5': 1, '6': 1, '7': 0, '8': 0, '9': 0, 'T': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1}
WONG_HALVES_VALUES = {'2': 0.5, '3': 1, '4': 1, '5': 1.5, '6': 1, '7': 0.5, '8': 0, '9': -0.5, 'T': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1}

class CardCounter:
    """A base class for a card counting system."""
    def __init__(self, num_decks=8):
        self.num_decks = num_decks
        self.running_count = 0.0
        self.seen_cards = 0
        self.count_values = {}

    def process_cards(self, card_ranks: list):
        """
        Processes a list of cards and updates the running count.
        """
        for rank in card_ranks:
            rank = rank.upper()
            if rank in self.count_values:
                self.running_count += self.count_values[rank]
                self.seen_cards += 1

    def get_running_count(self) -> float:
        """Returns the current running count."""
        return self.running_count

    def get_true_count(self) -> float:
        """
        Calculates and returns the true count.
        True Count = Running Count / Decks Remaining
        """
        total_cards = self.num_decks * 52
        if total_cards == self.seen_cards:
            return float('inf')

        decks_remaining = (total_cards - self.seen_cards) / 52
        if decks_remaining <= 0.5: # Unreliable when less than half a deck remains
            return float('inf')

        return self.running_count / decks_remaining

    def reset(self):
        """Resets the counter for a new shoe."""
        self.running_count = 0.0
        self.seen_cards = 0
        print(f"[{self.__class__.__name__}] Counter has been reset.")

class HiLoCounter(CardCounter):
    """Implements the Hi-Lo card counting system."""
    def __init__(self, num_decks=8):
        super().__init__(num_decks)
        self.count_values = HI_LO_VALUES

class WongHalvesCounter(CardCounter):
    """Implements the Wong Halves card counting system."""
    def __init__(self, num_decks=8):
        super().__init__(num_decks)
        self.count_values = WONG_HALVES_VALUES
