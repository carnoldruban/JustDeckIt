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
        self.composition_estimate = {CATEGORY_ACE: 0, CATEGORY_TEN: 0, CATEGORY_
LOW: 0, CATEGORY_NEUTRAL: 0, CATEGORY_OTHER: 0}
        self.total_cards_in_zone = len(self.cards)
        if not self.cards: return
        for card in self.cards:
            category = get_card_category(card)
            self.composition_estimate[category] = self.composition_estimate.get(
category, 0) + 1

    def get_composition_summary_dict(self) -> dict[str, tuple[int, float]]:
        if self.total_cards_in_zone == 0:
            return {cat: (0, 0.0) for cat in self.composition_estimate.keys()}
        summary_with_percentages = {}
        for category, count in self.composition_estimate.items():
            percentage = (count / self.total_cards_in_zone) * 100 if self.total_
cards_in_zone > 0 else 0.0
            summary_with_percentages[category] = (count, percentage)
        return summary_with_percentages

    def get_summary(self) -> str:
        display_id = self.id + 1
        if self.total_cards_in_zone == 0:
            return f"Zone {display_id} (0 cards): Empty"
        comp_summary_dict = self.get_composition_summary_dict()
        parts = [f"Zone {display_id} ({self.total_cards_in_zone} cards):"]
        ordered_categories = [CATEGORY_ACE, CATEGORY_TEN, CATEGORY_LOW, CATEGORY
_NEUTRAL, CATEGORY_OTHER]
        for category_key in ordered_categories:
            count, percentage = comp_summary_dict.get(category_key, (0, 0.0))
            category_display_name = category_key
            if category_key == CATEGORY_ACE: category_display_name = "Aces"
            elif category_key == CATEGORY_TEN: category_display_name = "Tens"
            elif category_key == CATEGORY_LOW: category_display_name = "Lows"
            elif category_key == CATEGORY_NEUTRAL: category_display_name = "Neut
rals"
            if category_key == CATEGORY_OTHER and count == 0: continue
            parts.append(f"{category_display_name}: {count} ({percentage:.2f}%)"
)
        return ", ".join(parts)

    def deal_card(self, specific_card: Optional['Card'] = None) -> Optional['Car
d']:
        if not self.cards: return None
        card_to_deal = None
        card_removed = False
        if specific_card:
            try:
                idx_to_remove = self.cards.index(specific_card)
                card_to_deal = self.cards.pop(idx_to_remove)
                card_removed = True
            except ValueError: return None
        else:
            card_to_deal = self.cards.pop(0)
            card_removed = True
        if card_removed: self.update_composition_estimate()
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
        """Creates a fresh, unshuffled list of cards for a given number of decks
."""
        # This static method relies on a function from the 'cards' module.
        # The import is structured to work whether the application is run as a s
cript or a module.
        try:
            from blackjack_tracker.core_logic.cards import create_shoe_cards
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
            if self.zones: self.current_dealing_zone_id = 0
            return
        total_cards = len(all_undealt_cards)
        base_size = total_cards // num_zones
        remainder = total_cards % num_zones
        current_pos = 0
        for i in range(num_zones):
            zone_size = base_size + (1 if i < remainder else 0)
            actual_zone_size = min(zone_size, total_cards - current_pos)
            zone_cards = all_undealt_cards[current_pos : current_pos + actual_zo
ne_size]
            self.zones.append(Zone(zone_id=i, cards=zone_cards))
            current_pos += actual_zone_size
        if self.zones: self.current_dealing_zone_id = 0

    def deal_card_from_current_zone(self, specific_card: Optional['Card'] = None
) -> Optional['Card']:
        if self.current_dealing_zone_id is None or not self.zones or self.curren
t_dealing_zone_id >= len(self.zones):
            return None
        dealt_card_from_zone = None
        start_zone_idx = self.current_dealing_zone_id
        for i in range(start_zone_idx, len(self.zones)):
            current_zone = self.zones[i]
            self.current_dealing_zone_id = i
            if specific_card:
                dealt_card_from_zone = current_zone.deal_card(specific_card=spec
ific_card)
                if dealt_card_from_zone: break
                else:
                    self.current_dealing_zone_id = start_zone_idx
                    return None
            else:
                dealt_card_from_zone = current_zone.deal_card()
                if dealt_card_from_zone: break
        if dealt_card_from_zone:
            try:
                self.shoe.undealt_cards.remove(dealt_card_from_zone) # Ensure co
nsistency with main shoe
            except ValueError:
                # This warning indicates a potential desync if the card was in z
one but not shoe.undealt_cards
                print(f"Warning: Card {dealt_card_from_zone} dealt from zone {se
lf.current_dealing_zone_id +1} but not found in main shoe.undealt_cards for remo
val.")
            return dealt_card_from_zone
        else:
            self.current_dealing_zone_id = None
            return None

    def get_all_zone_summaries(self) -> List[str]:
        if not self.zones: return ["Zone tracking is not active or no zones defi
ned."]
        return [zone.get_summary() for zone in self.zones]

    def get_current_dealing_zone_id_for_display(self) -> Optional[int]:
        if self.current_dealing_zone_id is None: return None
        return self.current_dealing_zone_id + 1

    @staticmethod
    def riffle_card_lists(list1: List['Card'], list2: List['Card'], imperfection
: float = 0.05) -> List['Card']:
        result = []
        deck1 = list(list1)
        deck2 = list(list2)
        while deck1 or deck2:
            clump1_size = random.randint(1, 3)
            if random.random() < imperfection and deck1: clump1_size = random.ra
ndint(2, 4)
            for _ in range(clump1_size):
                if deck1: result.append(deck1.pop(0))
                else: break
            clump2_size = random.randint(1, 3)
            if random.random() < imperfection and deck2: clump2_size = random.ra
ndint(2, 4)
            for _ in range(clump2_size):
                if deck2: result.append(deck2.pop(0))
                else: break
        return result

    @staticmethod
    def stack_card_lists(list_of_card_lists: List[List['Card']]) -> List['Card']
:
        combined_list: List['Card'] = []
        for card_list in list_of_card_lists:
            combined_list.extend(card_list)
        return combined_list

    @staticmethod
    def combine_card_lists(list1: List['Card'], list2: List['Card'], list1_on_to
p: bool) -> List['Card']:
        if list1_on_top: return list1 + list2
        else: return list2 + list1

    @staticmethod
    def split_list_into_two_halves(card_list: List['Card']) -> Tuple[List['Card'
], List['Card']]:
        if not card_list: return [], []
        midpoint = (len(card_list) + 1) // 2
        first_half = card_list[:midpoint]
        second_half = card_list[midpoint:]
        return first_half, second_half

    @staticmethod
    def split_list_into_k_chunks(card_list: List['Card'], k: int) -> List[List['
Card']]:
        if k <= 0: return []
        if not card_list: return [[] for _ in range(k)]
        n = len(card_list)
        if k == 1: return [list(card_list)]
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
        if not self.zones: return
        for op_tuple in operations:
            op_type = op_tuple[0]
            if op_type == "riffle" and len(op_tuple) == 4:
                try:
                    zone1_idx, zone2_idx, target_idx = int(op_tuple[1]), int(op_
tuple[2]), int(op_tuple[3])
                    if not (0 <= zone1_idx < len(self.zones) and \
                            0 <= zone2_idx < len(self.zones) and \
                            0 <= target_idx < len(self.zones)):
                        continue
                    zone1_cards = self.zones[zone1_idx].clear_cards()
                    zone2_cards = []
                    if zone1_idx != zone2_idx:
                        zone2_cards = self.zones[zone2_idx].clear_cards()
                    shuffled_cards = ShuffleManager.riffle_card_lists(zone1_card
s, zone2_cards)
                    self.zones[target_idx].add_cards(shuffled_cards)
                except (ValueError, IndexError) as e:
                    print(f"Error in riffle operation {op_tuple}: {e}")
                    continue
        new_undealt_pile: List['Card'] = []
        for zone in self.zones:
            new_undealt_pile.extend(zone.cards)
        self.shoe.undealt_cards = collections.deque(new_undealt_pile)
        self.initialize_zones(self.num_tracking_zones)

    def print_zone_summaries(self):
        if not self.zones:
            print("ShuffleManager: No zones initialized to print.")
            return
        for zone in self.zones:
            print(zone.get_summary())

    @staticmethod
    def strip_shuffle_pile(pile_to_strip: List['Card'], strip_packet_size_input:
 Optional[int]) -> List['Card']:
        """
        Performs a strip shuffle on a given pile of cards.
        Small packets are taken from the top of the input pile and placed on top
 of a new pile.
        This process effectively reverses the order of the packets.

        Args:
            pile_to_strip (List['Card']): The list of cards to be strip shuffled
.
            strip_packet_size_input (Optional[int]): The desired packet size for
 stripping.
                If None, 0, or invalid, a default size (approx. 1/7th of the pil
e) will be used.

        Returns:
            List['Card']: The strip-shuffled list of cards.
        """
        if not pile_to_strip:
            return []

        working_pile = list(pile_to_strip) # Create a copy to manipulate

        packet_size: int
        if strip_packet_size_input and strip_packet_size_input > 0:
            packet_size = strip_packet_size_input
        else:
            # Default packet size: aim for roughly 7 strips, ensure at least 1 c
ard per packet.
            packet_size = max(1, len(working_pile) // 7)
            if packet_size == 0 and len(working_pile) > 0 : # Handles very small
 piles len < 7
                packet_size = 1


        stripped_packets: List[List['Card']] = []
        while working_pile:
            current_packet_size = min(packet_size, len(working_pile))
            packet = working_pile[:current_packet_size]
            stripped_packets.append(packet)
            working_pile = working_pile[current_packet_size:]

        # The way a strip shuffle is described (taking from top of source, placi
ng on top of new pile)
        # means the first packet taken ends up at the bottom of the result.
        # So, we reverse the order of the packets themselves before concatenatin
g.
        final_shuffled_pile: List['Card'] = []
        for p in reversed(stripped_packets):
            final_shuffled_pile.extend(p)

        return final_shuffled_pile

if __name__ == '__main__':
    try:
        from cards import Card, Shoe
    except ImportError:
        print("Direct test: Could not import Card and Shoe. Using dummy classes.
")
        class Card:
            def __init__(self, suit: str, rank_str: str):
                self.suit = suit; self.rank_str = rank_str
                self.value = 0
                if rank_str == 'A': self.value = 11
                elif rank_str in ['K','Q','J','10']: self.value = 10
                elif rank_str.isdigit(): self.value = int(rank_str)
            def __str__(self): return f"{self.rank_str}{self.suit[0]}"
            def __repr__(self): return f"Card('{self.suit}','{self.rank_str}')"
            def __eq__(self, other): return isinstance(other, Card) and self.sui
t == other.suit and self.rank_str == other.rank_str
            def __hash__(self): return hash((self.suit, self.rank_str))
        class Shoe:
            def __init__(self, num_physical_decks=1):
                self.undealt_cards = collections.deque()
                ranks = "A23456789TJQK"; suits = "HDSC"
                for _ in range(num_physical_decks):
                    for r_ in ranks:
                        for s_ in suits: self.undealt_cards.append(Card(s_,r_))
                random.shuffle(self.undealt_cards)
            def __len__(self): return len(self.undealt_cards)

    print("--- Zone Tests ---")
    test_cards_for_zone = [Card("Hearts", "A"), Card("Spades", "K"), Card("Diamo
nds", "2")]
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
