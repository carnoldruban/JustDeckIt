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
        Removes observed cards from the undealt pile based on their rank,
        applying zone-swap synchronization logic:
          - If the next-to-be-dealt (front of undealt) matches the rank, remove it.
          - Otherwise, find the nearest occurrence (first match after the front) of that rank,
            swap it with the front card, then remove from the front.
          - If no matching rank exists anywhere, fall back to removing the front card
            to advance the pointer, and log a warning.
        Returns the removed card objects, preserving suit information.
        """
        removed_cards = []
        for rank_to_remove in card_ranks_to_remove:
            if not self.undealt_cards:
                print("Warning: Undealt shoe is empty while trying to remove cards.")
                break

            # Expected next card (pointer)
            expected_card = self.undealt_cards[0] if self.undealt_cards else None
            expected_rank = str(expected_card)[0] if expected_card else None

            # Case 1: Match at pointer
            if expected_rank == rank_to_remove:
                card_found_to_remove = self.undealt_cards.pop(0)
                self.dealt_cards.append(card_found_to_remove)
                removed_cards.append(card_found_to_remove)
                continue

            # Case 2: Mismatch -> find nearest occurrence from the front (first match after pointer)
            match_index = -1
            for i in range(1, len(self.undealt_cards)):
                if str(self.undealt_cards[i])[0] == rank_to_remove:
                    match_index = i
                    break

            if match_index != -1:
                # Swap nearest matching card with the pointer, then remove from front
                self.undealt_cards[0], self.undealt_cards[match_index] = (
                    self.undealt_cards[match_index],
                    self.undealt_cards[0],
                )
                card_found_to_remove = self.undealt_cards.pop(0)
                print(f"[Shoe] Mismatch resolved by nearest swap: expected {expected_card}, played {card_found_to_remove} (from idx {match_index})")
                self.dealt_cards.append(card_found_to_remove)
                removed_cards.append(card_found_to_remove)
            else:
                # Case 3: Could not find matching rank at all – advance pointer to stay in sync
                print(f"Warning: Could not find card with rank '{rank_to_remove}' anywhere in undealt. Advancing pointer past {expected_card}.")
                card_found_to_remove = self.undealt_cards.pop(0)
                self.dealt_cards.append(card_found_to_remove)
                removed_cards.append(card_found_to_remove)

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
