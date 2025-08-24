import collections

class Card:
    """Represents a single playing card."""
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.value = self._get_value()

    def _get_value(self):
        if self.rank.isdigit():
            return int(self.rank)
        elif self.rank in 'JQK':
            return 10
        else: # Ace
            return 11 # The logic for 1 or 11 is handled when calculating hand values

    def __str__(self):
        """The string representation is just its rank, for card counting purposes."""
        return self.rank

    def __repr__(self):
        return f"Card('{self.rank}', '{self.suit}')"

class StandardDeck:
    """Represents a standard 52-card deck."""
    ranks = [str(n) for n in range(2, 11)] + list('JQKA')
    suits = 'spades diamonds clubs hearts'.split()

    def __init__(self):
        self.cards = [Card(rank, suit) for suit in self.suits for rank in self.ranks]

    def __len__(self):
        return len(self.cards)

    def __getitem__(self, position):
        return self.cards[position]
