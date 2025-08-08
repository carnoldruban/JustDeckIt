from blackjack_tracker.core_logic.cards import Card, Shoe
from typing import List # Added for type hint

# Hi-Lo Card Counting System Values
# Maps card rank strings to their Hi-Lo count value.
HI_LO_VALUES = {
    # Low cards (2-6) increment the running count, indicating the shoe is richer in high cards.
    "2": 1, "3": 1, "4": 1, "5": 1, "6": 1,
    # Neutral cards (7-9) do not change the running count.
    "7": 0, "8": 0, "9": 0,
    # High cards (10, J, Q, K, A) decrement the running count, indicating fewer high cards remain.
    "10": -1, "J": -1, "Q": -1, "K": -1, "A": -1
}

class CardCounter:
    """
    Manages card counting logic for a Blackjack game, primarily using the Hi-Lo system.
    It tracks the running count, true count, and provides information about Aces.
    """
    def __init__(self, shoe_instance: Shoe):
        """
        Initializes the CardCounter with a specific Shoe instance.

        Args:
            shoe_instance (Shoe): The Shoe object that this counter will track.

        Raises:
            TypeError: If shoe_instance is not an instance of the Shoe class.
        """
        if not isinstance(shoe_instance, Shoe):
            raise TypeError("CardCounter must be initialized with a Shoe instance.")

        self.shoe: Shoe = shoe_instance  # Reference to the shoe being tracked
        self.running_count: int = 0      # Current Hi-Lo running count
        self.ace_count: int = 0          # Number of Aces dealt from the shoe

    def _get_card_value_hi_lo(self, card: Card) -> int:
        """
        Gets the Hi-Lo counting value of a single card.
        """
        if not isinstance(card, Card):
            raise TypeError("Can only get Hi-Lo value of a Card object.")
        return HI_LO_VALUES.get(card.rank_str, 0)

    def card_dealt(self, card: Card):
        """
        Updates the running count and Ace count when a single card is dealt from the shoe.
        """
        if not isinstance(card, Card):
            raise TypeError("Can only process a Card object being dealt.")

        self.running_count += self._get_card_value_hi_lo(card)
        if card.rank_str == "A":
            self.ace_count += 1

    def cards_dealt(self, list_of_cards: List[Card]):
        """
        Updates counts for a list of dealt cards by calling card_dealt for each.
        """
        for card in list_of_cards:
            self.card_dealt(card)

    def get_running_count(self) -> int:
        """Returns the current Hi-Lo running count."""
        return self.running_count

    def get_true_count(self) -> float:
        """
        Calculates the true count.
        """
        remaining_decks = self.shoe.get_remaining_decks_approx()
        if remaining_decks <= 0:
            if self.running_count > 0: return float('inf')
            if self.running_count < 0: return float('-inf')
            return 0.0
        true_val = self.running_count / remaining_decks
        return true_val

    def get_ace_count(self) -> int:
        """Returns the total number of Aces that have been dealt from this shoe."""
        return self.ace_count

    def get_remaining_aces(self) -> int:
        """
        Calculates the estimated number of Aces remaining in the undealt portion of the shoe.
        """
        total_aces_at_start = self.shoe.num_physical_decks * 4
        return total_aces_at_start - self.ace_count

    def reset_counts_for_new_shoe(self):
        """
        Resets the running count and Ace count to zero.
        """
        self.running_count = 0
        self.ace_count = 0

    def reset_round_specific_counts(self):
        pass # Placeholder as per Gist

if __name__ == '__main__':
    my_shoe = Shoe(num_physical_decks=2)
    counter = CardCounter(my_shoe)
    print(f"Initial state: RC: {counter.get_running_count()}, TC: {counter.get_true_count():.2f}, Aces Dealt: {counter.get_ace_count()}, Rem Aces: {counter.get_remaining_aces()}")
    dealt_in_round1 = []
    cards_to_deal_specs_r1 = [("Hearts", "A"), ("Spades", "K"), ("Diamonds", "5"), ("Clubs", "7"), ("Hearts", "A")]
    print("\n--- Round 1 ---")
    for suit, rank in cards_to_deal_specs_r1:
        card_to_find = Card(suit, rank)
        dealt_card = my_shoe.deal_card(specific_card_to_remove=card_to_find)
        if dealt_card: dealt_in_round1.append(dealt_card); print(f"  Shoe dealt: {dealt_card}")
        else: dealt_card = my_shoe.deal_card();
        if dealt_card: dealt_in_round1.append(dealt_card); print(f"  Shoe dealt from top: {dealt_card}")
    counter.cards_dealt(dealt_in_round1)
    my_shoe.end_round()
    print(f"After {len(dealt_in_round1)} cards: RC: {counter.get_running_count()}, TC: {counter.get_true_count():.2f}, Aces Dealt: {counter.get_ace_count()}, Rem Aces: {counter.get_remaining_aces()}")
    my_shoe.collect_cards_and_shuffle()
    counter.reset_counts_for_new_shoe()
    print(f"After reshuffle & reset: RC: {counter.get_running_count()}, TC: {counter.get_true_count():.2f}, Aces Dealt: {counter.get_ace_count()}, Rem Aces: {counter.get_remaining_aces()}")