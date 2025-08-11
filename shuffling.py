import random
import math
import collections
from typing import List, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from cards import Card, Shoe, create_shoe_cards

ACE_RANK_STR = "A"
TEN_VALUE_RANKS = ["10", "J", "Q", "K"]

CATEGORY_ACE = "Ace"
CATEGORY_TEN = "Ten"
CATEGORY_LOW = "Low"
CATEGORY_NEUTRAL = "Neutral"
CATEGORY_OTHER = "Other"

def get_card_category(card: 'Card') -> str:
    if card.rank_str == ACE_RANK_STR:
        return CATEGORY_ACE
    elif card.rank_str in TEN_VALUE_RANKS:
        return CATEGORY_TEN
    elif card.value >= 2 and card.value <= 6:
        return CATEGORY_LOW
    elif card.value >= 7 and card.value <= 9:
        return CATEGORY_NEUTRAL
    else:
        return CATEGORY_OTHER

class Zone:
    def __init__(self, zone_id: int, cards: Optional[List['Card']] = None):
        self.id: int = zone_id
        self.cards: List['Card'] = list(cards) if cards is not None else []
        self.composition_estimate: dict[str, int] = {}
        self.total_cards_in_zone: int = 0
        self.update_composition_estimate()

    def update_composition_estimate(self):
        self.composition_estimate = {CATEGORY_ACE: 0, CATEGORY_TEN: 0, CATEGORY_LOW: 0, CATEGORY_NEUTRAL: 0, CATEGORY_OTHER: 0}
        self.total_cards_in_zone = len(self.cards)
        if not self.cards:
            return
        for card in self.cards:
            category = get_card_category(card)
            self.composition_estimate[category] = self.composition_estimate.get(category, 0) + 1

    def get_composition_summary_dict(self) -> dict[str, tuple[int, float]]:
        if self.total_cards_in_zone == 0:
            return {cat: (0, 0.0) for cat in self.composition_estimate.keys()}
        summary_with_percentages = {}
        for category, count in self.composition_estimate.items():
            percentage = (count / self.total_cards_in_zone) * 100 if self.total_cards_in_zone > 0 else 0.0
            summary_with_percentages[category] = (count, percentage)
        return summary_with_percentages

    def get_summary(self) -> str:
        display_id = self.id + 1
        if self.total_cards_in_zone == 0:
            return f"Zone {display_id} (0 cards): Empty"
        comp_summary_dict = self.get_composition_summary_dict()
        parts = [f"Zone {display_id} ({self.total_cards_in_zone} cards):"]
        ordered_categories = [CATEGORY_ACE, CATEGORY_TEN, CATEGORY_LOW, CATEGORY_NEUTRAL, CATEGORY_OTHER]
        for category_key in ordered_categories:
            count, percentage = comp_summary_dict.get(category_key, (0, 0.0))
            category_display_name = category_key
            if category_key == CATEGORY_ACE:
                category_display_name = "Aces"
            elif category_key == CATEGORY_TEN:
                category_display_name = "Tens"
            elif category_key == CATEGORY_LOW:
                category_display_name = "Lows"
            elif category_key == CATEGORY_NEUTRAL:
                category_display_name = "Neutrals"
            if category_key == CATEGORY_OTHER and count == 0:
                continue
            parts.append(f"{category_display_name}: {count} ({percentage:.2f}%)")
        return ", ".join(parts)

    def deal_card(self, specific_card: Optional['Card'] = None) -> Optional['Card']:
        if not self.cards:
            return None
        card_to_deal = None
        card_removed = False
        if specific_card:
            try:
                idx_to_remove = self.cards.index(specific_card)
                card_to_deal = self.cards.pop(idx_to_remove)
                card_removed = True
            except ValueError:
                return None
        else:
            card_to_deal = self.cards.pop(0)
            card_removed = True
        if card_removed:
            self.update_composition_estimate()
        return card_to_deal

    def add_cards(self, new_cards: List['Card'], to_top: bool = False):
        if to_top:
            self.cards = new_cards + self.cards
        else:
            self.cards.extend(new_cards)
        self.update_composition_estimate()

    def clear_cards(self) -> List['Card']:
        removed_cards = list(self.cards)
        self.cards = []
        self.update_composition_estimate()
        return removed_cards

    def __len__(self) -> int:
        return self.total_cards_in_zone

class ShuffleManager:
    def __init__(self, shoe: 'Shoe', num_tracking_zones: int = 0):
        self.shoe: 'Shoe' = shoe
        self.zones: List[Zone] = []
        self.current_dealing_zone_id: Optional[int] = None
        if num_tracking_zones > 0:
            self.initialize_zones(num_tracking_zones)

    @staticmethod
    def create_fresh_shoe_cards(num_decks: int) -> List['Card']:
        """Creates a fresh, unshuffled list of cards for a given number of decks."""
        try:
            from cards import create_shoe_cards
        except ImportError:
            from cards import create_shoe_cards
        return create_shoe_cards(num_decks)

    def initialize_zones(self, num_zones: int):
        if num_zones <= 0:
            self.zones = []
            self.current_dealing_zone_id = None
            return
        all_undealt_cards = list(self.shoe.undealt_cards)
        if not all_undealt_cards:
            for i in range(num_zones):
                self.zones.append(Zone(zone_id=i, cards=[]))
            if self.zones:
                self.current_dealing_zone_id = 0
            return
        total_cards = len(all_undealt_cards)
        base_size = total_cards // num_zones
        remainder = total_cards % num_zones
        current_pos = 0
        for i in range(num_zones):
            zone_size = base_size + (1 if i < remainder else 0)
            actual_zone_size = min(zone_size, total_cards - current_pos)
            zone_cards = all_undealt_cards[current_pos : current_pos + actual_zone_size]
            self.zones.append(Zone(zone_id=i, cards=zone_cards))
            current_pos += actual_zone_size
        if self.zones:
            self.current_dealing_zone_id = 0

    def deal_card_from_current_zone(self, specific_card: Optional['Card'] = None) -> Optional['Card']:
        if self.current_dealing_zone_id is None or not self.zones or self.current_dealing_zone_id >= len(self.zones):
            return None
        dealt_card_from_zone = None
        start_zone_idx = self.current_dealing_zone_id
        for i in range(start_zone_idx, len(self.zones)):
            current_zone = self.zones[i]
            self.current_dealing_zone_id = i
            if specific_card:
                dealt_card_from_zone = current_zone.deal_card(specific_card=specific_card)
                if dealt_card_from_zone:
                    break
                else:
                    self.current_dealing_zone_id = start_zone_idx
                    return None
            else:
                dealt_card_from_zone = current_zone.deal_card()
                if dealt_card_from_zone:
                    break
        if dealt_card_from_zone:
            try:
                self.shoe.undealt_cards.remove(dealt_card_from_zone)
            except ValueError:
                print(f"Warning: Card {dealt_card_from_zone} dealt from zone {self.current_dealing_zone_id +1} but not found in main shoe.undealt_cards for removal.")
            return dealt_card_from_zone
        else:
            self.current_dealing_zone_id = None
            return None

    def get_all_zone_summaries(self) -> List[str]:
        if not self.zones:
            return ["Zone tracking is not active or no zones defined."]
        return [zone.get_summary() for zone in self.zones]

    def get_current_dealing_zone_id_for_display(self) -> Optional[int]:
        if self.current_dealing_zone_id is None:
            return None
        return self.current_dealing_zone_id + 1

    @staticmethod
    def riffle_card_lists(list1: List['Card'], list2: List['Card'], imperfection: float = 0.05) -> List['Card']:
        result = []
        deck1 = list(list1)
        deck2 = list(list2)
        while deck1 or deck2:
            clump1_size = random.randint(1, 3)
            if random.random() < imperfection and deck1:
                clump1_size = random.randint(2, 4)
            for _ in range(clump1_size):
                if deck1:
                    result.append(deck1.pop(0))
                else:
                    break
            clump2_size = random.randint(1, 3)
            if random.random() < imperfection and deck2:
                clump2_size = random.randint(2, 4)
            for _ in range(clump2_size):
                if deck2:
                    result.append(deck2.pop(0))
                else:
                    break
        return result

    @staticmethod
    def stack_card_lists(list_of_card_lists: List[List['Card']]) -> List['Card']:
        combined_list: List['Card'] = []
        for card_list in list_of_card_lists:
            combined_list.extend(card_list)
        return combined_list

    @staticmethod
    def combine_card_lists(list1: List['Card'], list2: List['Card'], list1_on_top: bool) -> List['Card']:
        if list1_on_top:
            return list1 + list2
        else:
            return list2 + list1

    @staticmethod
    def split_list_into_two_halves(card_list: List['Card']) -> Tuple[List['Card'], List['Card']]:
        if not card_list:
            return [], []
        midpoint = (len(card_list) + 1) // 2
        first_half = card_list[:midpoint]
        second_half = card_list[midpoint:]
        return first_half, second_half

    @staticmethod
    def split_list_into_k_chunks(card_list: List['Card'], k: int) -> List[List['Card']]:
        if k <= 0:
            return []
        if not card_list:
            return [[] for _ in range(k)]
        n = len(card_list)
        if k == 1:
            return [list(card_list)]
        if k > n:
            chunks = [[card] for card in card_list]
            chunks.extend([[] for _ in range(k - n)])
            return chunks
        base_chunk_size = n // k
        remainder = n % k
        chunks = []
        current_pos = 0
        for i in range(k):
            chunk_size = base_chunk_size + (1 if i < remainder else 0)
            chunk = card_list[current_pos : current_pos + chunk_size]
            chunks.append(chunk)
            current_pos += chunk_size
        return chunks

    def perform_tracked_shuffle(self, operations: List[Tuple[str, ...]]):
        if not self.zones:
            return
        for op_tuple in operations:
            op_type = op_tuple[0]
            if op_type == "riffle" and len(op_tuple) == 4:
                try:
                    zone1_idx, zone2_idx, target_idx = int(op_tuple[1]), int(op_tuple[2]), int(op_tuple[3])
                    if not (0 <= zone1_idx < len(self.zones) and 0 <= zone2_idx < len(self.zones) and 0 <= target_idx < len(self.zones)):
                        continue
                    zone1_cards = self.zones[zone1_idx].clear_cards()
                    zone2_cards = []
                    if zone1_idx != zone2_idx:
                        zone2_cards = self.zones[zone2_idx].clear_cards()
                    shuffled_cards = ShuffleManager.riffle_card_lists(zone1_cards, zone2_cards)
                    self.zones[target_idx].add_cards(shuffled_cards)
                except (ValueError, IndexError) as e:
                    print(f"Error in riffle operation {op_tuple}: {e}")
                    continue
        new_undealt_pile: List['Card'] = []
        for zone in self.zones:
            new_undealt_pile.extend(zone.cards)
        self.shoe.undealt_cards = collections.deque(new_undealt_pile)
        self.initialize_zones(len(self.zones))

    def perform_full_shoe_shuffle(self):
        """
        Implements the user-defined multi-stage shoe shuffling algorithm.
        """
        print("Starting new user-defined full shoe shuffle...")

        # 1. Combine unplayed and discarded cards into a single shuffling stack
        # Per user: "last round first card for dealer will be the top card of the discarded cards which will be the top of shuffling stack"
        # This means discard pile goes on top of the remaining undealt cards.
        shuffling_stack = self.shoe.discard_pile + list(self.shoe.undealt_cards)
        self.shoe.discard_pile.clear()
        self.shoe.undealt_cards.clear()

        if not shuffling_stack:
            print("Shoe is empty, nothing to shuffle.")
            return

        print(f"Initial shuffling stack size: {len(shuffling_stack)}")

        # --- Main Shuffle Loop (3 iterations) ---
        for i in range(3):
            print(f"\n--- Starting Iteration {i+1}/4 ---")

            # a. Split the stack into Side A and Side B
            side_a, side_b = self.split_list_into_two_halves(shuffling_stack)
            print(f"  - Split into Side A ({len(side_a)} cards) and Side B ({len(side_b)} cards)")

            # b. Split each side into 8 chunks
            chunks_a = self.split_list_into_k_chunks(side_a, 8)
            chunks_b = self.split_list_into_k_chunks(side_b, 8)
            print(f"  - Split sides into {len(chunks_a)} and {len(chunks_b)} chunks.")

            # c. Riffle corresponding chunks
            riffled_results = []
            for j in range(8):
                chunk_a = chunks_a[j] if j < len(chunks_a) else []
                chunk_b = chunks_b[j] if j < len(chunks_b) else []
                riffled_chunk = self.riffle_card_lists(chunk_a, chunk_b)
                riffled_results.append(riffled_chunk)
            print(f"  - Riffled 8 pairs of chunks.")

            # d. Reassemble the stack with chunk 8 on top, chunk 1 at the bottom
            shuffling_stack = []
            for chunk in reversed(riffled_results):
                shuffling_stack.extend(chunk)
            print(f"  - Reassembled stack. New size: {len(shuffling_stack)}")

        # --- Step 3: Implement Special 4th Iteration ---
        print("\n--- Starting Special Iteration 4/4 ---")
        # The shuffling_stack from the first 3 iterations is used here
        side_a, side_b = self.split_list_into_two_halves(shuffling_stack)
        print(f"  - Split into Side A ({len(side_a)} cards) and Side B ({len(side_b)} cards)")

        chunks_a = self.split_list_into_k_chunks(side_a, 8)
        chunks_b = self.split_list_into_k_chunks(side_b, 8)
        print(f"  - Split sides into {len(chunks_a)} and {len(chunks_b)} chunks.")

        fourth_iteration_results = []
        for j in range(8):
            print(f"    - Processing chunk pair {j+1}/8...")
            chunk_a = chunks_a[j] if j < len(chunks_a) else []
            chunk_b = chunks_b[j] if j < len(chunks_b) else []

            # a. Riffle
            riffled_chunk = self.riffle_card_lists(chunk_a, chunk_b)

            # b. Hindu Shuffle
            hindu_shuffled_chunk = self.hindu_shuffle(riffled_chunk)

            # c. Split and Riffle again
            half1, half2 = self.split_list_into_two_halves(hindu_shuffled_chunk)
            final_chunk_result = self.riffle_card_lists(half1, half2)

            fourth_iteration_results.append(final_chunk_result)

        # Reassemble the stack in reverse order
        shuffling_stack = []
        for chunk in reversed(fourth_iteration_results):
            shuffling_stack.extend(chunk)
        print(f"  - Reassembled stack after 4th iteration. New size: {len(shuffling_stack)}")

        # --- Step 4: Implement Final Cut ---
        print("\n--- Performing Final Cut ---")
        top_half, bottom_half = self.split_list_into_two_halves(shuffling_stack)
        shuffling_stack = bottom_half + top_half
        print(f"  - Final cut complete. The bottom {len(bottom_half)} cards are now on top.")

        # Update the shoe object with the newly shuffled deck
        self.shoe.undealt_cards = collections.deque(shuffling_stack)
        print(f"\nShuffle complete. Shoe now has {len(self.shoe.undealt_cards)} cards.")

        # Re-initialize zones if they are being used
        if self.zones:
            self.initialize_zones(len(self.zones))

    def print_zone_summaries(self):
        if not self.zones:
            print("ShuffleManager: No zones initialized to print.")
            return
        for zone in self.zones:
            print(zone.get_summary())

    @staticmethod
    def hindu_shuffle(card_list: List['Card'], packet_size_input: Optional[int] = None) -> List['Card']:
        """
        Performs a Hindu shuffle (also known as a strip or running cut).
        Small packets are taken from the top of the deck and placed in reverse order,
        simulating them being dropped on top of each other on a table.
        The original top of the deck becomes the new bottom.
        """
        if not card_list:
            return []

        working_pile = list(card_list)
        packet_size: int
        if packet_size_input and packet_size_input > 0:
            packet_size = packet_size_input
        else:
            # Use a reasonable default packet size
            packet_size = max(1, len(working_pile) // 7) if len(working_pile) > 7 else 1

        stripped_packets: List[List['Card']] = []
        while working_pile:
            current_packet_size = min(packet_size, len(working_pile))
            packet = working_pile[:current_packet_size]
            stripped_packets.append(packet)
            working_pile = working_pile[current_packet_size:]

        final_shuffled_pile: List['Card'] = []
        for p in reversed(stripped_packets):
            final_shuffled_pile.extend(p)
        return final_shuffled_pile

if __name__ == '__main__':
    try:
        from cards import Card, Shoe
    except ImportError:
        print("Direct test: Could not import Card and Shoe. Using dummy classes.")
        class Card:
            def __init__(self, suit: str, rank_str: str):
                self.suit = suit
                self.rank_str = rank_str
                self.value = 0
                if rank_str == 'A':
                    self.value = 11
                elif rank_str in ['K', 'Q', 'J', '10']:
                    self.value = 10
                elif rank_str.isdigit():
                    self.value = int(rank_str)
            def __str__(self):
                return f"{self.rank_str}{self.suit[0]}"
            def __repr__(self):
                return f"Card('{self.suit}','{self.rank_str}')"
            def __eq__(self, other):
                return isinstance(other, Card) and self.suit == other.suit and self.rank_str == other.rank_str
            def __hash__(self):
                return hash((self.suit, self.rank_str))
        class Shoe:
            def __init__(self, num_physical_decks=1):
                self.undealt_cards = collections.deque()
                self.discard_pile = []
                ranks = "A23456789TJQK"
                suits = "HDSC"
                for _ in range(num_physical_decks):
                    for r_ in ranks:
                        for s_ in suits:
                            self.undealt_cards.append(Card(s_, r_))
                random.shuffle(self.undealt_cards)
            def __len__(self):
                return len(self.undealt_cards)

    print("--- Zone Tests ---")
    test_cards_for_zone = [Card("Hearts", "A"), Card("Spades", "K"), Card("Diamonds", "2")]
    zone1 = Zone(zone_id=0, cards=test_cards_for_zone)
    print(f"Zone 1 initial: {zone1.get_summary()}")

    print("\n--- ShuffleManager Static Method Tests ---")
    deck_half1 = [Card("Hearts", "A"), Card("Spades", "2")]
    deck_half2 = [Card("Diamonds", "K"), Card("Clubs", "Q")]
    riffled = ShuffleManager.riffle_card_lists(deck_half1, deck_half2)
    print(f"Riffled simple: {[str(c) for c in riffled]}")

    print("\n--- ShuffleManager Integration Tests ---")
    my_shoe = Shoe(num_physical_decks=1)
    manager = ShuffleManager(my_shoe, num_tracking_zones=4)
    if manager.zones:
        print(f"Manager initialized with {len(manager.zones)} zones.")
        manager.print_zone_summaries()
        print("\nPerforming test tracked riffle shuffle (Zone 1+2 -> Zone 1):")
        manager.perform_tracked_shuffle([("riffle", 0, 1, 0)])
        print("\nZone summaries after tracked shuffle:")
        manager.print_zone_summaries()

    print("\n--- Hindu Shuffle Test ---")
    test_ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J']
    test_deck_hindu = [Card("Spades", r) for r in test_ranks] # 10 cards
    print(f"Original deck for Hindu shuffle: {[str(c) for c in test_deck_hindu]}")
    hindu_shuffled_deck = ShuffleManager.hindu_shuffle(test_deck_hindu, packet_size_input=3)
    print(f"Hindu shuffled deck (packet size 3): {[str(c) for c in hindu_shuffled_deck]}")

    print("\n--- Full Shoe Shuffle Test ---")
    # Create a shoe with 8 decks as per user requirements
    full_shoe = Shoe(num_physical_decks=8)
    print(f"Created a shoe with {len(full_shoe.undealt_cards)} cards ({len(full_shoe.undealt_cards)/52.0:.1f} decks).")
    # Move some cards to discard to simulate a used shoe
    for _ in range(150):
        if full_shoe.undealt_cards:
            full_shoe.discard_pile.append(full_shoe.undealt_cards.popleft())

    shuffle_manager_for_full_test = ShuffleManager(full_shoe)
    shuffle_manager_for_full_test.perform_full_shoe_shuffle()
    print("--- Full Shoe Shuffle Test Complete ---")
