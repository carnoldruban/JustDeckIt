import random

class Shoe:
    """
    Represents a shoe of cards. This class is now stateless and operates on
    card lists provided to it, primarily for analysis.
    """
    def __init__(self, undealt_cards=None, dealt_cards=None):
        self.undealt_cards = undealt_cards if undealt_cards is not None else []
        self.dealt_cards = dealt_cards if dealt_cards is not None else []

    @staticmethod
    def create_new_shuffled_shoe(num_decks=8):
        """Creates a new, shuffled list of cards."""
        print(f"[Shoe] Creating a new shuffled shoe with {num_decks} decks.")
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        suits = ['H', 'D', 'C', 'S']
        new_shoe = [f"{r}{s}" for _ in range(num_decks) for r in ranks for s in suits]
        random.shuffle(new_shoe)
        return new_shoe

    def remove_cards(self, card_ranks_to_remove):
        """
        Removes observed cards from the undealt pile based on their rank.
        Returns the removed card objects.
        """
        removed_cards = []
        for rank_to_remove in card_ranks_to_remove:
            card_found_to_remove = None
            for i, card in enumerate(self.undealt_cards):
                if str(card)[0] == rank_to_remove:  # Match rank (first character)
                    card_found_to_remove = self.undealt_cards.pop(i)
                    break

            if card_found_to_remove:
                self.dealt_cards.append(card_found_to_remove)
                removed_cards.append(card_found_to_remove)
            else:
                # This might happen if the shoe is out of sync with the game
                print(f"Warning: Could not find card with rank '{rank_to_remove}' in shoe to remove.")
        
        return removed_cards

    def get_zone_info(self, num_zones=8):
        """
        Analyzes the composition of the undealt cards by dividing them into zones.
        """
        zone_size = len(self.undealt_cards) // num_zones
        zones = {}
        for i in range(num_zones):
            zone_name = f"Zone {i+1}"
            start_index = i * zone_size
            end_index = start_index + zone_size if i < num_zones - 1 else len(self.undealt_cards)
            zone_cards = self.undealt_cards[start_index:end_index]
            
            if not zone_cards:
                zones[zone_name] = {'total': 0, 'low_pct': 0, 'mid_pct': 0, 'high_pct': 0}
                continue

            low_cards = len([c for c in zone_cards if c[0] in '23456'])
            mid_cards = len([c for c in zone_cards if c[0] in '789'])
            high_cards = len([c for c in zone_cards if c[0] in 'TJQKA'])
            
            zones[zone_name] = {
                'total': len(zone_cards),
                'low_pct': (low_cards / len(zone_cards)) * 100,
                'mid_pct': (mid_cards / len(zone_cards)) * 100,
                'high_pct': (high_cards / len(zone_cards)) * 100
            }
        return zones

    def get_card_zone(self, card, num_zones=8):
        """Determines which zone a card belongs to."""
        try:
            index = self.undealt_cards.index(card)
            zone_size = len(self.undealt_cards) // num_zones
            return (index // zone_size) + 1
        except (ValueError, ZeroDivisionError):
            return None