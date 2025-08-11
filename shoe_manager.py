from cards import Card, Shoe
from shuffling import ShuffleManager

class ShoeManager:
    def __init__(self, default_regions=8):
        self.default_regions = default_regions
        self.shoes = {
            "None": None,
            "Shoe 1": self._create_new_tracked_shoe(),
            "Shoe 2": self._create_new_tracked_shoe()
        }
        self.shuffle_managers = {
            "Shoe 1": ShuffleManager(self.shoes["Shoe 1"], self.default_regions),
            "Shoe 2": ShuffleManager(self.shoes["Shoe 2"], self.default_regions)
        }
        self.active_shoe_name = "None"
        self.unshuffled_cards = []

    def _create_new_tracked_shoe(self) -> Shoe:
        """Creates a fresh, randomly shuffled 8-deck shoe."""
        return Shoe(num_physical_decks=8, shuffle_now=True)

    def get_active_shoe(self) -> Shoe | None:
        return self.shoes.get(self.active_shoe_name)

    def set_active_shoe(self, name: str):
        if name in self.shoes:
            self.active_shoe_name = name
            print(f"Active shoe set to: {name}")
        else:
            print(f"Error: Shoe '{name}' not found.")

    def end_current_shoe(self):
        """
        Marks the current shoe as finished, starts shuffling it in the background,
        and switches the active shoe.
        """
        if self.active_shoe_name == "None":
            print("No active shoe selected to mark as ended.")
            return False

        if self.shuffle_thread and self.shuffle_thread.is_alive():
            print("A shuffle is already in progress. Please wait for it to complete.")
            return False

        shoe_to_shuffle_name = self.active_shoe_name
        shuffle_manager_instance = self.shuffle_managers[shoe_to_shuffle_name]

        print(f"Ending {shoe_to_shuffle_name}. It will be shuffled in the background.")

        # The `perform_full_shoe_shuffle` method now handles combining the cards.
        self.shuffle_thread = threading.Thread(target=shuffle_manager_instance.perform_full_shoe_shuffle, daemon=True)
        self.shuffle_thread.start()

        # Immediately switch to the other shoe so play can continue
        next_shoe = "Shoe 2" if self.active_shoe_name == "Shoe 1" else "Shoe 1"
        self.set_active_shoe(next_shoe)

        return True

    def process_discard_logic(self, payload: dict):
        """Processes a game payload and adds played cards to the discard pile of the active shoe."""
        active_shoe = self.get_active_shoe()
        if not active_shoe:
            return # Not tracking, so do nothing

        # This logic needs to be precise as per user's request
        # For now, we'll just collect all cards. The precise ordering will be a refinement.
        all_played_cards = []
        dealer_hand = payload.get('dealer', {})
        if dealer_hand.get('cards'):
            for card_data in dealer_hand['cards']:
                # Need to convert string back to Card object
                # This requires a helper function
                pass # Placeholder

        # This part is complex because the JSON gives us strings, but Shoe object needs Card objects.
        # We need a way to map the string from JSON back to the specific Card instance in the shoe.
        # This requires a significant change in how we track cards.

        # For now, we will placeholder this logic.
        # A proper implementation needs to map the dealt card strings to the actual Card objects
        # that were dealt from the Shoe's undealt_cards deque.
        pass

    def _card_from_string(self, card_str: str) -> Card | None:
        """Helper to create a Card object from a string like 'KH' or 'T_S'."""
        if not card_str or len(card_str) < 2 or card_str == "**":
            return None

        rank = card_str[0].upper()
        suit_char = card_str[1].upper()

        suits_map = {'H': 'Hearts', 'D': 'Diamonds', 'C': 'Clubs', 'S': 'Spades'}
        if suit_char not in suits_map:
            return None

        # Handle Ten, which is 'T' in our JSON
        if rank == 'T':
            rank = '10'

        return Card(suits_map[suit_char], rank)

    def process_game_state(self, payload: dict):
        """
        Processes a game state payload, dealing cards from the active shoe
        and moving them to the discard pile in the correct order.
        Returns a list of newly dealt Card objects.
        """
        active_shoe = self.get_active_shoe()
        if not active_shoe:
            return [] # Not tracking, do nothing

        # 1. Gather all card strings from the payload in the specified discard order.
        ordered_card_strings = []
        dealer_hand = payload.get('dealer', {})
        if dealer_hand.get('cards'):
            # Per user spec: dealer's first card, then hole card, then rest.
            dealer_cards_json = dealer_hand['cards']
            if len(dealer_cards_json) > 0:
                ordered_card_strings.append(dealer_cards_json[0]['value'])
            if len(dealer_cards_json) > 1:
                ordered_card_strings.append(dealer_cards_json[1]['value'])
            if len(dealer_cards_json) > 2:
                for card_data in dealer_cards_json[2:]:
                    ordered_card_strings.append(card_data['value'])

        seats = payload.get('seats', {})
        for i in range(7): # Iterate 0 through 6 to maintain order
            seat_data = seats.get(str(i))
            if seat_data and seat_data.get('first', {}).get('cards'):
                 for card_data in seat_data['first']['cards']:
                     ordered_card_strings.append(card_data['value'])
                # Handle split hands in the future if necessary

        # 2. For each card string, find and "deal" the specific card from the shoe
        newly_dealt_cards = []
        for card_str in ordered_card_strings:
            card_obj = self._card_from_string(card_str)
            if card_obj:
                # The shoe's deal_card method handles moving it from undealt to dealt_this_round
                dealt_card = active_shoe.deal_card(specific_card_to_remove=card_obj)
                if dealt_card:
                    # Check if this is the first time we are seeing this card in this round
                    if dealt_card not in newly_dealt_cards:
                         newly_dealt_cards.append(dealt_card)

        # 3. Finalize the round by moving all dealt cards to the discard pile
        active_shoe.end_round()

        print(f"Processed round. Discard pile size: {len(active_shoe.discard_pile)}")
        return newly_dealt_cards

    def perform_shuffle(self, target_shoe_name: str, shuffle_params: dict):
        """Uses the ShuffleManager to shuffle the saved cards and updates a shoe."""
        if not self.unshuffled_cards:
            print("No cards available to shuffle.")
            return

        if target_shoe_name not in self.shoes or target_shoe_name == "None":
            print(f"Invalid target shoe for shuffling: {target_shoe_name}")
            return

        # Create a temporary Shoe object with the unshuffled cards to pass to the ShuffleManager
        temp_shoe = Shoe(num_physical_decks=0, shuffle_now=False)
        temp_shoe.undealt_cards = collections.deque(self.unshuffled_cards)

        # Initialize the shuffle manager with zones based on form input
        try:
            num_zones = int(shuffle_params.get("regions", 4))
        except (ValueError, TypeError):
            num_zones = 4

        shuffle_manager = ShuffleManager(temp_shoe, num_tracking_zones=num_zones)

        # This is a placeholder for a complex series of shuffle operations.
        # A real implementation would generate these from the form.
        # For now, we will simulate a simple shuffle: riffle the first two zones into the first zone.
        if num_zones >= 2:
            print(f"Performing tracked shuffle on {len(self.unshuffled_cards)} cards...")
            shuffle_operations = [("riffle", 0, 1, 0)]
            shuffle_manager.perform_tracked_shuffle(shuffle_operations)
        else:
            # If not enough zones, just do a random shuffle
            print("Not enough zones for tracked shuffle, performing random shuffle.")
            random.shuffle(list(shuffle_manager.shoe.undealt_cards))


        # Update the target shoe with the new shuffled (predicted) deck
        self.shoes[target_shoe_name].undealt_cards = shuffle_manager.shoe.undealt_cards

        print(f"{target_shoe_name} has been updated with a new predicted deck of {len(self.shoes[target_shoe_name].undealt_cards)} cards.")
        self.unshuffled_cards = [] # Clear the temporary pile
