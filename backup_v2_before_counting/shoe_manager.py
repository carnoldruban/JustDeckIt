from shoe import Shoe
from collections import Counter, deque
from shuffling import perform_full_shuffle
import threading

class ShoeManager:
    """Manages multiple shoes and the active shoe for tracking."""
    def __init__(self):
        self.shoes = {
            "Shoe 1": Shoe(),
            "Shoe 2": Shoe()
        }
        self.active_shoe_name = "None"
        self.round_card_cache = {}
        self.shuffle_thread = None
        self.last_dealt_card = None

    def set_active_shoe(self, shoe_name):
        """Sets the currently active shoe for tracking."""
        self.active_shoe_name = shoe_name
        self.round_card_cache = {}
        if shoe_name != "None":
            print(f"[ShoeManager] Active shoe set to: {shoe_name}")
        else:
            print("[ShoeManager] Shoe tracking disabled.")

    def get_active_shoe(self):
        """Returns the active shoe object, or None."""
        return self.shoes.get(self.active_shoe_name)

    def get_last_dealt_card(self):
        """Returns the last card that was dealt."""
        return self.last_dealt_card

    def process_game_state(self, payload):
        """
        Processes a payload to find new cards and removes them from the active shoe.
        Returns a list of newly dealt card objects.
        """
        game_id = payload.get('gameId')
        if not game_id:
            return []

        all_cards_in_payload = []
        if 'dealer' in payload and payload['dealer'].get('cards'):
            all_cards_in_payload.extend([c['value'] for c in payload['dealer']['cards'] if c.get('value') != '**'])
        if 'seats' in payload:
            for seat in payload['seats'].values():
                if seat.get('first', {}).get('cards'):
                    all_cards_in_payload.extend([c['value'] for c in seat['first']['cards']])

        if game_id not in self.round_card_cache:
            if len(self.round_card_cache) > 10:
                self.round_card_cache.clear()
            self.round_card_cache[game_id] = []

        payload_counts = Counter(all_cards_in_payload)
        seen_counts = Counter(self.round_card_cache.get(game_id, []))

        newly_dealt_card_ranks = []
        for card_rank, count in payload_counts.items():
            new_count = count - seen_counts.get(card_rank, 0)
            if new_count > 0:
                newly_dealt_card_ranks.extend([card_rank] * new_count)

        self.round_card_cache[game_id] = all_cards_in_payload

        active_shoe = self.get_active_shoe()
        if active_shoe and newly_dealt_card_ranks:
            dealt_card_objects = active_shoe.remove_cards(newly_dealt_card_ranks)
            if dealt_card_objects:
                self.last_dealt_card = dealt_card_objects[-1] # Store the last card object
            print(f"[ShoeManager] Removed {newly_dealt_card_ranks} from {self.active_shoe_name}")
            return dealt_card_objects

        return []

    def end_current_shoe_and_shuffle(self, shuffle_params):
        """
        Marks the end of the current shoe, then shuffles it in a background thread.
        """
        shoe_to_shuffle = self.get_active_shoe()
        if not shoe_to_shuffle:
            return False

        if self.shuffle_thread and self.shuffle_thread.is_alive():
            return False

        shuffling_stack = shoe_to_shuffle.dealt_cards + list(shoe_to_shuffle.undealt_cards)

        if not shuffling_stack:
            self.shoes[self.active_shoe_name] = Shoe()
            return True

        self.shuffle_thread = threading.Thread(
            target=self._shuffle_worker,
            args=(self.active_shoe_name, shuffling_stack, shuffle_params),
            daemon=True
        )
        self.shuffle_thread.start()
        return True

    def _shuffle_worker(self, shoe_name, stack, params):
        """The actual shuffling work, done in a background thread."""
        num_iterations = int(params.get('iterations', 4))
        num_chunks = int(params.get('chunks', 8))

        shuffled_deck = perform_full_shuffle(stack, num_iterations, num_chunks)

        new_shoe = Shoe(num_decks=0)
        new_shoe.undealt_cards = deque(shuffled_deck)
        new_shoe.dealt_cards = []
        self.shoes[shoe_name] = new_shoe

        print(f"[ShuffleWorker] Shuffle for {shoe_name} complete.")
