from typing import Optional, List, Dict, Any, Tuple
import collections

from blackjack_tracker.core_logic.cards import Shoe, Card
from blackjack_tracker.core_logic.counting import CardCounter # Ensure this import is correct
from blackjack_tracker.core_logic.shuffling import ShuffleManager, Zone

class BlackjackTracker:
    def __init__(self, num_physical_decks: int = 6, num_tracking_zones: int = 0,
                 hi_lo_true_count_precision: int = 2): # hi_lo_true_count_precision is kept for now, though CardCounter doesn't use it in __init__
        self.num_physical_decks = num_physical_decks
        self.num_tracking_zones = num_tracking_zones
        self.shoe: Shoe = Shoe(num_physical_decks)

        # Correctly instantiate CardCounter using the shoe_instance
        self.counter: CardCounter = CardCounter(shoe_instance=self.shoe)
        # If true_count_precision were to be used by CardCounter, it might be set as an attribute after init,
        # or passed to a method that uses it, e.g., self.counter.true_count_precision = hi_lo_true_count_precision
        # For now, we rely on the CardCounter's internal logic for true count calculation.

        self.shuffle_manager: Optional[ShuffleManager] = None
        if self.num_tracking_zones > 0:
            self.shuffle_manager = ShuffleManager(shoe_instance=self.shoe, num_zones=self.num_tracking_zones)

    def set_number_of_tracking_zones(self, num_zones: int):
        self.num_tracking_zones = num_zones
        if self.num_tracking_zones > 0:
            if self.shuffle_manager:
                self.shuffle_manager.initialize_zones(self.num_tracking_zones)
            else:
                self.shuffle_manager = ShuffleManager(shoe_instance=self.shoe, num_zones=self.num_tracking_zones)
        else:
            self.shuffle_manager = None

    def deal_card_from_shoe(self, specific_card: Optional[Card] = None) -> Optional[Card]:
        dealt_card_obj: Optional[Card] = None
        if specific_card:
            dealt_card_obj = self.shoe.deal_card(specific_card_to_remove=specific_card)
            if dealt_card_obj and self.shuffle_manager and self.shuffle_manager.zones:
                for zone in self.shuffle_manager.zones:
                    if zone.deal_card(specific_card=dealt_card_obj):
                        break
        else:
            if self.shuffle_manager and self.shuffle_manager.zones:
                dealt_card_obj = self.shuffle_manager.deal_card_from_current_zone(specific_card=None)
                if dealt_card_obj and dealt_card_obj not in self.shoe.dealt_this_round:
                    self.shoe.dealt_this_round.append(dealt_card_obj)
            else:
                dealt_card_obj = self.shoe.deal_card(specific_card_to_remove=None)

        if dealt_card_obj:
            num_remaining_in_shoe_after_deal = len(self.shoe.undealt_cards)
            # The CardCounter's card_dealt method (from Gist) does not take num_remaining_cards_in_shoe
            # It relies on its self.shoe reference for true count calculation.
            self.counter.card_dealt(dealt_card_obj) # Corrected from add_card to card_dealt
        return dealt_card_obj

    def end_round(self):
        self.shoe.end_round()
        self.counter.reset_round_specific_counts() # This was in Gist's tracker.py, CardCounter has it as pass

    def perform_tracked_shuffle(self, shuffle_operations: List[Tuple[str, ...]]):
        if not self.shuffle_manager:
            return
        self.shuffle_manager.perform_tracked_shuffle(shuffle_operations)
        # CardCounter's reset_counts_for_new_shoe (from Gist) doesn't take num_decks
        self.counter.reset_counts_for_new_shoe()

    def full_random_reshuffle(self):
        self.shoe.collect_cards_and_shuffle(shuffle_type="standard_random")
        self.counter.reset_counts_for_new_shoe() # Corrected: no args as per Gist's CardCounter
        if self.shuffle_manager:
            self.shuffle_manager.initialize_zones(self.num_tracking_zones)

    def get_tracking_info(self) -> Dict[str, Any]:
        num_remaining_cards_for_tc = len(self.shoe.undealt_cards)
        zone_summaries_list: List[str] = []
        current_dealing_zone_id_for_info: Optional[int] = None

        if self.shuffle_manager and self.shuffle_manager.zones:
            zone_summaries_list = self.shuffle_manager.get_all_zone_summaries()
            current_dealing_zone_id_for_info = self.shuffle_manager.current_dealing_zone_id

        approx_decks_rem = self.shoe.get_remaining_decks_approx() # Use shoe's method
        true_count_val = self.counter.get_true_count() # get_true_count in Gist's CardCounter takes no args

        # Apply precision if it was meant to be stored or passed differently
        # For now, we use the raw float from get_true_count.
        # If hi_lo_true_count_precision was stored in self.counter, it could be used here.
        # true_count_display = float(f"{true_count_val:.{self.counter.true_count_precision}f}") if hasattr(self.counter, 'true_count_precision') else true_count_val

        remaining_aces_val = self.counter.get_remaining_aces() # Corrected method name from Gist

        info: Dict[str, Any] = {
            "running_count": self.counter.running_count, # Direct attribute access
            "true_count": true_count_val, # Raw value from counter
            "aces_dealt": self.counter.ace_count, # Direct attribute access
            "remaining_aces": remaining_aces_val,
            "cards_in_shoe": num_remaining_cards_for_tc,
            "approx_decks_remaining": approx_decks_rem,
            "zone_summaries": zone_summaries_list,
            "current_dealing_zone_id": current_dealing_zone_id_for_info
        }
        return info

if __name__ == '__main__':
    print("--- BlackjackTracker Basic Tests (1 Deck, No Zones) ---")
    # Pass hi_lo_true_count_precision if tracker's __init__ still takes it,
    # even if CardCounter __init__ doesn't use it directly.
    tracker = BlackjackTracker(num_physical_decks=1, num_tracking_zones=0, hi_lo_true_count_precision=2)
    print(f"Initial state: {tracker.get_tracking_info()}")
    print("\nDealing 5 cards:")
    cards_to_try_deal = [Card("Hearts", "A"), Card("Spades", "5"), Card("Diamonds", "K"), Card("Clubs", "2"), Card("Hearts", "7")]
    for card_to_deal in cards_to_try_deal:
        print(f"Attempting to deal: {card_to_deal}")
        dealt_c = tracker.deal_card_from_shoe(specific_card=card_to_deal)
        if dealt_c:
            # Access true_count from get_tracking_info for consistent formatting if applied there
            tc_display = tracker.get_tracking_info()['true_count']
            print(f"Successfully Dealt: {dealt_c}, RC: {tracker.counter.running_count}, TC: {tc_display:.2f}")
        else:
            print(f"Could not deal {card_to_deal} (not found or shoe empty).")

    print(f"\nState after attempts: {tracker.get_tracking_info()}")
    tracker.end_round()
    print(f"State after end_round (discards: {len(tracker.shoe.discard_pile)}): {tracker.get_tracking_info()}")

    print("\n--- BlackjackTracker with Zone Tracking (1 Deck, 2 Zones) ---")
    tracker_zoned = BlackjackTracker(num_physical_decks=1, num_tracking_zones=2)
    print(f"Initial state (1 deck, 2 zones):")
    initial_info_zoned = tracker_zoned.get_tracking_info()
    for key, val in initial_info_zoned.items():
        if key == "zone_summaries": print(f"  {key}:"); [print(f"    {s}") for s in val]
        else: print(f"  {key}: {val}")

    print("\nDealing 3 cards (specifically) with zones active:")
    if tracker_zoned.shoe.undealt_cards and len(tracker_zoned.shoe.undealt_cards) >=3:
        # Create card instances based on what might be at the top of the shoe for testing
        # This is still a bit artificial without peeking into zones directly for specific cards
        # but simulates UI sending specific cards that are expected to be in the shoe.

        # Let's assume these cards are present and attempt to deal them.
        # The new deal_card_from_shoe logic will search the whole shoe, then update zones.
        cards_to_deal_zoned_known = [
            Card(tracker_zoned.shoe.undealt_cards[0].suit, tracker_zoned.shoe.undealt_cards[0].rank_str),
            Card(tracker_zoned.shoe.undealt_cards[1].suit, tracker_zoned.shoe.undealt_cards[1].rank_str),
            Card(tracker_zoned.shoe.undealt_cards[2].suit, tracker_zoned.shoe.undealt_cards[2].rank_str),
        ]

        for card_to_deal_z in cards_to_deal_zoned_known:
            print(f"Attempting to deal specific: {card_to_deal_z}")
            dealt_c_zoned = tracker_zoned.deal_card_from_shoe(specific_card=card_to_deal_z)
            if dealt_c_zoned:
                info = tracker_zoned.get_tracking_info()
                display_zone_id = (info['current_dealing_zone_id'] + 1) if info['current_dealing_zone_id'] is not None else "N/A"
                tc_display_zoned = info['true_count']
                print(f"Dealt: {dealt_c_zoned}, RC: {info['running_count']}, TC: {tc_display_zoned:.2f}, From Zone Display: {display_zone_id}")
            else:
                print(f"Could not deal specific {card_to_deal_z}."); break
    else:
        print("Not enough cards in shoe for zoned specific deal test.")

    print(f"\nState after 3 specific cards (zoned):")
    info_after_3_zoned = tracker_zoned.get_tracking_info()
    for key, val in info_after_3_zoned.items():
        if key == "zone_summaries": print(f"  {key}:"); [print(f"    {s}") for s in val]
        else: print(f"  {key}: {val}")

    print("\nSimulating a tracked shuffle (riffle zones 0 and 1, result to zone 0) for zoned tracker:")
    if tracker_zoned.shuffle_manager:
        tracker_zoned.perform_tracked_shuffle([("riffle", 0, 1, 0)])
        print("\nState after tracked shuffle (zoned):")
        info_after_shuffle_zoned = tracker_zoned.get_tracking_info()
        for key, val in info_after_shuffle_zoned.items():
            if key == "zone_summaries": print(f"  {key}:"); [print(f"    {s}") for s in val]
            else: print(f"  {key}: {val}")
    else:
        print("  Skipping tracked shuffle test as shuffle_manager is not active.")

    print("\nSimulating full random reshuffle for zoned tracker:")
    tracker_zoned.full_random_reshuffle()
    print("\nState after full random reshuffle (zoned):")
    info_after_full_reshuffle = tracker_zoned.get_tracking_info()
    for key, val in info_after_full_reshuffle.items():
        if key == "zone_summaries": print(f"  {key}:"); [print(f"    {s}") for s in val]
        else: print(f"  {key}: {val}")
    print(f"  Shoe undealt card count: {len(tracker_zoned.shoe.undealt_cards)}")