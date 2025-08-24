from shoe import Shoe
from collections import Counter
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

    def process_game_state(self, payload):
        """
        Processes a payload to find new cards and removes them from the active shoe.
        This logic will be restored in a future step. For now, it's a placeholder.
        """
        # This logic is complex and will be added back when we integrate card tracking.
        return []

    def end_current_shoe_and_shuffle(self, shuffle_params):
        """
        Marks the end of the current shoe, then shuffles it in a background thread
        using the provided parameters.
        """
        shoe_to_shuffle = self.get_active_shoe()
        if not shoe_to_shuffle:
            print("[ShoeManager] No active shoe to end.")
            return False

        if self.shuffle_thread and self.shuffle_thread.is_alive():
            print("[ShoeManager] A shuffle is already in progress. Please wait.")
            return False

        print(f"[ShoeManager] Ending shoe: {self.active_shoe_name}. It will be shuffled in the background.")

        # Combine dealt and undealt cards to form the full stack for shuffling
        shuffling_stack = shoe_to_shuffle.dealt_cards + list(shoe_to_shuffle.undealt_cards)

        # Start the shuffle in a new thread to avoid freezing the UI
        self.shuffle_thread = threading.Thread(
            target=self._shuffle_worker,
            args=(self.active_shoe_name, shuffling_stack, shuffle_params),
            daemon=True
        )
        self.shuffle_thread.start()
        return True

    def _shuffle_worker(self, shoe_name, stack, params):
        """The actual shuffling work, done in a background thread."""
        print(f"[ShuffleWorker] Starting shuffle for {shoe_name} with {len(stack)} cards.")
        num_iterations = int(params.get('iterations', 4))
        num_chunks = int(params.get('chunks', 8))

        shuffled_deck = perform_full_shuffle(stack, num_iterations, num_chunks)

        # Replace the old shoe with a new one containing the shuffled deck
        new_shoe = Shoe(num_decks=0) # Create an empty shoe
        new_shoe.undealt_cards = deque(shuffled_deck)
        new_shoe.dealt_cards = []
        self.shoes[shoe_name] = new_shoe

        print(f"[ShuffleWorker] Shuffle for {shoe_name} complete. New deck is ready.")
