import random
from cards import StandardDeck

class Shoe:
    """Represents the collection of cards used in a game, typically multiple decks."""
    def __init__(self, num_decks=8):
        self.num_decks = num_decks
        self.undealt_cards = []
        self.dealt_cards = []
        self.reset()

    def reset(self):
        """Resets the shoe to a full, ordered state and shuffles it."""
        self.undealt_cards = []
        for _ in range(self.num_decks):
            self.undealt_cards.extend(StandardDeck().cards)
        self.dealt_cards = []
        self.shuffle()

    def shuffle(self):
        """Shuffles the undealt cards."""
        random.shuffle(self.undealt_cards)
        print(f"Shoe with {len(self.undealt_cards)} cards has been shuffled.")

    def remove_cards(self, card_ranks_to_remove):
        """
        Removes observed cards from the undealt pile based on their rank.
        This is used when tracking a live game, where we don't 'deal' but 'observe'.
        """
        for rank_to_remove in card_ranks_to_remove:
            card_found_to_remove = None
            for card in self.undealt_cards:
                if str(card) == rank_to_remove:
                    card_found_to_remove = card
                    break

            if card_found_to_remove:
                self.undealt_cards.remove(card_found_to_remove)
                self.dealt_cards.append(card_found_to_remove)
            else:
                # This might happen if the shoe is out of sync with the game
                print(f"Warning: Could not find card with rank '{rank_to_remove}' in shoe to remove.")

    def get_penetration(self):
        """Calculates the percentage of cards that have been dealt from the shoe."""
        total_cards = len(self.undealt_cards) + len(self.dealt_cards)
        if total_cards == 0:
            return 0.0
        return (len(self.dealt_cards) / total_cards) * 100

    def get_zone_info(self, num_zones=8):
        """
        Divides the undealt cards into zones and returns a summary of each zone.
        """
        if not self.undealt_cards:
            return {}

        zone_size = (len(self.undealt_cards) + num_zones - 1) // num_zones
        zones = [list(self.undealt_cards)[i:i + zone_size] for i in range(0, len(self.undealt_cards), zone_size)]

        zone_summaries = {}
        from card_counter import HIGH_CARDS, LOW_CARDS, MIDDLE_CARDS

        for i, zone in enumerate(zones):
            if not zone: continue
            total_cards = len(zone)
            high = sum(1 for card in zone if str(card) in HIGH_CARDS)
            low = sum(1 for card in zone if str(card) in LOW_CARDS)
            mid = sum(1 for card in zone if str(card) in MIDDLE_CARDS)

            zone_summaries[f"Zone {i+1}"] = {
                "total": total_cards,
                "high_pct": (high / total_cards) * 100 if total_cards > 0 else 0,
                "low_pct": (low / total_cards) * 100 if total_cards > 0 else 0,
                "mid_pct": (mid / total_cards) * 100 if total_cards > 0 else 0,
            }
        return zone_summaries

    def get_card_zone(self, card_to_find, num_zones=8):
        """
        Finds which zone a specific card is currently in.
        Returns the zone number (1-based) or None if not found.
        """
        if not self.undealt_cards:
            return None

        try:
            # Find the index of the card in the flat list of undealt cards
            idx = list(self.undealt_cards).index(card_to_find)
            zone_size = (len(self.undealt_cards) + num_zones - 1) // num_zones
            # Calculate the zone number based on the index
            return (idx // zone_size) + 1
        except ValueError:
            # Card not found in undealt pile (it may have been dealt)
            return None
