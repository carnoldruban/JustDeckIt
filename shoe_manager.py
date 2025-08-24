from shoe import Shoe
from collections import Counter, deque
from shuffling import perform_full_shuffle
import threading
from logging_config import get_logger, log_performance

class ShoeManager:
    def __init__(self, db_manager=None):
        self.logger = get_logger("ShoeManager")
        self.db_manager = db_manager
        self.shoes = {
            "Shoe 1": Shoe(),
            "Shoe 2": Shoe()
        }
        self.active_shoe_name = "None"
        self.round_card_cache = {}
        self.shuffle_thread = None
        self.last_dealt_card = None
        self.shuffle_lock = threading.Lock()  # Add thread lock for shuffle operations
        
        self.logger.info("ShoeManager initialized with database manager: %s", db_manager is not None)
        self.logger.debug("Initial shoes: %s", list(self.shoes.keys()))

    @log_performance
    def set_active_shoe(self, shoe_name):
        self.logger.info("Setting active shoe to: %s", shoe_name)
        self.active_shoe_name = shoe_name
        self.round_card_cache = {}
        
        # Initialize shoe if it doesn't exist or is empty
        if shoe_name not in self.shoes or not self.shoes[shoe_name].undealt_cards:
            self.logger.info("Initializing new shoe: %s", shoe_name)
            self.shoes[shoe_name] = Shoe()
            # Create a new shuffled shoe
            new_cards = Shoe.create_new_shuffled_shoe(8)  # 8 decks
            self.shoes[shoe_name].undealt_cards = deque(new_cards)
            self.shoes[shoe_name].dealt_cards = []
            
            self.logger.debug("Created new shoe with %d cards", len(new_cards))
            
            # Update database
            if self.db_manager:
                self.db_manager.update_shoe_cards(
                    shoe_name,
                    list(self.shoes[shoe_name].undealt_cards),
                    list(self.shoes[shoe_name].dealt_cards)
                )
                self.logger.debug("Updated database with new shoe cards")
        
        if shoe_name != "None":
            self.logger.info("Active shoe set to: %s", shoe_name)
        else:
            self.logger.info("Shoe tracking disabled")

    def get_active_shoe(self):
        return self.shoes.get(self.active_shoe_name)

    def get_last_dealt_card(self):
        return self.last_dealt_card

    @log_performance
    def process_game_state(self, payload):
        self.logger.debug("Processing game state payload")
        game_id = payload.get('gameId')
        if not game_id:
            self.logger.warning("No game ID in payload")
            return []

        all_cards_in_payload = []
        if 'dealer' in payload and payload['dealer'].get('cards'):
            # CORRECTED: Extract only the first character for the rank
            dealer_cards = [c['value'][0] for c in payload['dealer']['cards'] if c.get('value') and c.get('value') != '**']
            all_cards_in_payload.extend(dealer_cards)
            self.logger.debug("Extracted dealer cards: %s", dealer_cards)
            
        if 'seats' in payload:
            for seat_num, seat in payload['seats'].items():
                if seat.get('first', {}).get('cards'):
                    # CORRECTED: Extract only the first character for the rank
                    seat_cards = [c['value'][0] for c in seat['first']['cards'] if c.get('value')]
                    all_cards_in_payload.extend(seat_cards)
                    self.logger.debug("Extracted seat %s cards: %s", seat_num, seat_cards)
        
        self.logger.debug("Total cards in payload: %s", all_cards_in_payload)
        
        if game_id not in self.round_card_cache:
            if len(self.round_card_cache) > 10:
                self.logger.debug("Clearing round card cache (size: %d)", len(self.round_card_cache))
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

        self.logger.debug("Newly dealt cards: %s", newly_dealt_card_ranks)

        active_shoe = self.get_active_shoe()
        if active_shoe and newly_dealt_card_ranks:
            dealt_card_objects = active_shoe.remove_cards(newly_dealt_card_ranks)
            if dealt_card_objects:
                self.last_dealt_card = dealt_card_objects[-1]
            self.logger.info("Removed %s cards from %s", newly_dealt_card_ranks, self.active_shoe_name)
            
            # Update database with current shoe state
            if self.db_manager:
                self.db_manager.update_shoe_cards(
                    self.active_shoe_name,
                    list(active_shoe.undealt_cards),
                    list(active_shoe.dealt_cards)
                )
                self.logger.debug("Updated database with current shoe state")
            
            return dealt_card_objects
        
        return []

    def end_current_shoe_and_shuffle(self, shuffle_params):
        with self.shuffle_lock:  # Use thread lock to prevent race conditions
            shoe_to_shuffle = self.get_active_shoe()
            if not shoe_to_shuffle: return False
            if self.shuffle_thread and self.shuffle_thread.is_alive(): return False

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
        num_iterations = int(params.get('iterations', 4))
        num_chunks = int(params.get('chunks', 8))
        shuffled_deck = perform_full_shuffle(stack, num_iterations, num_chunks)
        
        new_shoe = Shoe(num_decks=0)
        new_shoe.undealt_cards = deque(shuffled_deck)
        new_shoe.dealt_cards = []
        self.shoes[shoe_name] = new_shoe
        
        # Update database with new shuffled shoe
        if self.db_manager:
            self.db_manager.update_shoe_cards(
                shoe_name,
                list(new_shoe.undealt_cards),
                list(new_shoe.dealt_cards)
            )
        
        print(f"[ShuffleWorker] Shuffle for {shoe_name} complete.")