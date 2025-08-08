import random
import collections # Added for Shoe.undealt_cards to be a deque
from typing import Optional, List # Added Optional and List for type hints

# Define standard suits and their conventional symbols for display (optional)
SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
SUIT_SYMBOLS = {"Hearts": "♥", "Diamonds": "♦", "Clubs": "♣", "Spades": "♠"}

# Define standard card ranks and their Blackjack values
# Aces are initially 11, but game logic can change them to 1.
RANKS = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "10": 10, "J": 10, "Q": 10, "K": 10, "A": 11
}

class Card:
    """
    Represents a single playing card with a suit, rank string, and Blackjack val
ue.
    """
    def __init__(self, suit: str, rank_str: str):
        """
        Initializes a Card object.

        Args:
            suit (str): The suit of the card (e.g., "Hearts", "Spades").
                        Must be one of the defined SUITS.
            rank_str (str): The string representation of the card's rank (e.g.,
"A", "K", "10", "2").
                            Must be a key in the defined RANKS.

        Raises:
            ValueError: If the provided suit or rank_str is invalid.
        """
        if suit not in SUITS:
            raise ValueError(f"Invalid suit: {suit}. Must be one of {SUITS}")
        if rank_str not in RANKS:
            raise ValueError(f"Invalid rank string: {rank_str}. Must be one of {
list(RANKS.keys())}")

        self.suit = suit
        self.rank_str = rank_str
        self.value = RANKS[rank_str]

    def __str__(self):
        return f"{self.rank_str}{self.suit[0]}"

    def __repr__(self):
        return f"Card('{self.suit}', '{self.rank_str}')"

    def __eq__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        return self.suit == other.suit and self.rank_str == other.rank_str

    def __hash__(self):
        return hash((self.suit, self.rank_str))


def create_deck() -> List[Card]: # Changed to List[Card]
    """Creates a standard 52-card deck."""
    return [Card(suit, r_str) for suit in SUITS for r_str in RANKS.keys()]

def create_shoe_cards(num_decks: int) -> List[Card]:
    """Creates a list of cards for a shoe with a given number of decks."""
    if num_decks < 1:
        num_decks = 1
    shoe_cards = []
    for _ in range(num_decks):
        shoe_cards.extend(create_deck())
    return shoe_cards

class Deck:
    """Represents one or more physical decks, shuffled together."""
    def __init__(self, num_physical_decks: int = 1):
        self.cards: List[Card] = [] # Changed to List[Card]
        if num_physical_decks < 1:
            num_physical_decks = 1
        for _ in range(num_physical_decks):
            self.cards.extend(create_deck())
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def deal_card(self) -> Optional[Card]: # Changed to Optional[Card]
        if not self.cards:
            return None
        return self.cards.pop(0)

    def __len__(self) -> int:
        return len(self.cards)

class Shoe:
    """Manages undealt cards, current round dealt cards, and discard pile."""
    def __init__(self, num_physical_decks: int = 6, shuffle_now: bool = True):
        if num_physical_decks < 1:
            num_physical_decks = 1
        self.num_physical_decks: int = num_physical_decks
        _master_deck_cards = create_shoe_cards(num_physical_decks)
        if shuffle_now:
            random.shuffle(_master_deck_cards)
        # Shoe.undealt_cards is a deque for efficient pop from left (dealing)
        self.undealt_cards: collections.deque[Card] = collections.deque(_master_
deck_cards)
        self.dealt_this_round: List[Card] = [] # Changed to List[Card]
        self.discard_pile: List[Card] = []   # Changed to List[Card]

    def deal_card(self, specific_card_to_remove: Optional[Card] = None) -> Optio
nal[Card]:
        if not self.undealt_cards:
            return None

        card_to_deal: Optional[Card] = None
        if specific_card_to_remove:
            try:
                # Efficient removal from deque if card is found
                self.undealt_cards.remove(specific_card_to_remove) # Relies on C
ard.__eq__
                card_to_deal = specific_card_to_remove
            except ValueError: # Card not in deque
                return None
        else: # Deal from the "top" (left of deque)
            card_to_deal = self.undealt_cards.popleft()

        if card_to_deal:
            self.dealt_this_round.append(card_to_deal)
        return card_to_deal

    def end_round(self):
        self.discard_pile.extend(self.dealt_this_round)
        self.dealt_this_round = []

    def collect_cards_and_shuffle(self, shuffle_type: str = "standard_random"):
        all_cards_list = list(self.discard_pile) + list(self.undealt_cards) + li
st(self.dealt_this_round)
        self.discard_pile = []
        self.dealt_this_round = []

        if not all_cards_list:
            self.undealt_cards = collections.deque()
            return

        if shuffle_type == "standard_random":
            random.shuffle(all_cards_list)
        else:
            # Fallback or specific shuffle logic
            random.shuffle(all_cards_list)
        self.undealt_cards = collections.deque(all_cards_list)


    def set_initial_cards(self, card_list_tuples: List[tuple[str, str]]): # Chan
ged to List
        try:
            new_cards = [Card(s, r) for s, r in card_list_tuples]
            self.undealt_cards = collections.deque(new_cards)
        except ValueError as e:
            print(f"Error creating cards for set_initial_cards: {e}")
            raise
        self.dealt_this_round = []
        self.discard_pile = []
        self.num_physical_decks = round(len(self.undealt_cards) / 52.0)
        if self.num_physical_decks == 0 and len(self.undealt_cards) > 0:
            self.num_physical_decks = 1

    def get_remaining_decks_approx(self) -> float:
        if not self.undealt_cards: return 0.0
        return len(self.undealt_cards) / 52.0

    def __str__(self) -> str:
        return (f"Shoe: {len(self.undealt_cards)} undealt, "
                f"{len(self.dealt_this_round)} dealt this round, "
                f"{len(self.discard_pile)} in discard.")

    def __len__(self) -> int:
        return len(self.undealt_cards)

if __name__ == '__main__':
    ace_hearts = Card("Hearts", "A")
    king_spades = Card("Spades", "K")
    print(f"Card examples: {ace_hearts} (Value: {ace_hearts.value}), {king_spade
s} (Value: {king_spades.value})")
    single_deck_list = create_deck()
    print(f"\nStandard deck created with {len(single_deck_list)} cards.")
    shoe = Shoe(num_physical_decks=2)
    print(f"\n{shoe}")
    print("\nDealing 5 cards from shoe (from top):")
    for i in range(5):
        c = shoe.deal_card()
        if c: print(f"Dealt {i+1}: {c}")
    shoe.end_round()
    print(f"\nAfter ending round: {shoe}")
    shoe.collect_cards_and_shuffle()
    print(f"\nAfter reshuffle: {shoe}")
    custom_card_data = [("Hearts", "A"), ("Spades", "K"), ("Diamonds", "Q"), ("C
lubs", "J")]
    shoe.set_initial_cards(custom_card_data)
    print(f"\nShoe set with custom cards: {shoe}")
    ace_to_deal = Card("Hearts", "A")
    dealt_specific = shoe.deal_card(specific_card_to_remove=ace_to_deal)
    print(f"Dealt specific '{ace_to_deal}': {dealt_specific}, Shoe state: {shoe}
")
