from shoe import Shoe
from collections import Counter, deque
from shuffling import perform_full_shuffle
import threading
import json
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
        # NOTE: removed shuffle lock to avoid threading contention in tests/runtime
        self._last_game_id = None  # Track last processed game id for round boundary
        
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
            self.shoes[shoe_name].undealt_cards = list(new_cards)
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
        """Process payload, maintain current_dealt by t-ascending, and finalize previous round on gameId change."""
        self.logger.debug("Processing game state payload")
        gid = payload.get('gameId')
        if not gid:
            self.logger.warning("No game ID in payload")
            return []

        prev_gid = getattr(self, "_last_game_id", None)
        if prev_gid and prev_gid != gid:
            try:
                self._finalize_previous_round(prev_gid)
            except Exception as e:
                self.logger.error("Finalize previous round error: %s", e)

        # Build current-round dealt from visible cards sorted by timestamp 't'
        items = []
        # Dealer cards
        if payload.get('dealer', {}).get('cards'):
            for c in payload['dealer']['cards']:
                if isinstance(c, dict) and c.get('value') and c.get('value') != '**':
                    items.append((c['value'], c.get('t', 0)))
        # Seats cards
        for seat_key, seat in (payload.get('seats') or {}).items():
            first = seat.get('first', {})
            for c in (first.get('cards') or []):
                if isinstance(c, dict) and c.get('value') and c.get('value') != '**':
                    items.append((c['value'], c.get('t', 0)))
        items.sort(key=lambda x: x[1])
        current_round_dealt = [v for (v, _) in items]

        # Persist current_dealt for active shoe
        if self.db_manager is not None:
            try:
                self.db_manager.update_current_dealt_cards(self.active_shoe_name, current_round_dealt)
            except Exception as e:
                self.logger.error("update_current_dealt_cards error: %s", e)

        # Track last dealt (for UI convenience)
        if current_round_dealt:
            self.last_dealt_card = current_round_dealt[-1]

        self._last_game_id = gid
        return []

    def end_current_shoe_and_shuffle(self, shuffle_params):
        """
        New flow:
        - For the ACTIVE shoe A: compute shuffling stack = undealt(A) + discarded(A), store in DB.next_shuffling_stack(A)
        - Prepare the OTHER shoe B: shuffle B using its next_shuffling_stack(B) if present, else fresh/new
        """
        # Avoid concurrent shuffles
        if self.shuffle_thread and self.shuffle_thread.is_alive():
            return False

        active_name = self.active_shoe_name
        if not active_name or active_name == "None":
            return False

        # Compute and persist next_shuffling_stack for the active shoe (A)
        try:
            if self.db_manager:
                stateA = self.db_manager.get_shoe_state(active_name)
                # Build shuffling stack as (undealt + discarded) then reverse so top is dealer's last-round first card
                stackA_forward = list(stateA.get("undealt", [])) + list(stateA.get("discarded", []))
                stackA = list(reversed(stackA_forward))
                self.db_manager.set_next_shuffling_stack(active_name, stackA)
                print(f"[ShoeManager] Stored next_shuffling_stack for {active_name}: {len(stackA)} cards (reversed from undealt+discarded)")
        except Exception as e:
            print(f"[ShoeManager] Warning: failed to set next_shuffling_stack for {active_name}: {e}")

        # Prepare the other shoe (B) for play
        other_name = "Shoe 2" if active_name == "Shoe 1" else "Shoe 1"

        def worker(shoe_name, params):
            try:
                iterations = int(params.get('iterations', 4))
                chunks = int(params.get('chunks', 8))
                seed = params.get('seed')
                stackB = []
                if self.db_manager:
                    stateB = self.db_manager.get_shoe_state(shoe_name)
                    stackB = list(stateB.get("next_stack", []))

                if stackB:
                    shuffled_deck = perform_full_shuffle(stackB, iterations, chunks, seed=seed)
                else:
                    # Fallback: new shuffled 8-deck shoe
                    shuffled_deck = Shoe.create_new_shuffled_shoe(8)

                # Update in-memory shoe
                new_shoe = Shoe()
                new_shoe.undealt_cards = list(shuffled_deck)
                new_shoe.dealt_cards = []
                self.shoes[shoe_name] = new_shoe

                # Persist DB state for the prepared shoe
                if self.db_manager:
                    self.db_manager.update_shoe_cards(shoe_name, list(shuffled_deck), [])
                    self.db_manager.update_current_dealt_cards(shoe_name, [])
                    self.db_manager.set_discarded_cards(shoe_name, [])
                    self.db_manager.set_next_shuffling_stack(shoe_name, [])
                print(f"[ShuffleWorker] Prepared next shoe: {shoe_name} with {len(shuffled_deck)} cards.")
            except Exception as e:
                print(f"[ShuffleWorker] Error: {e}")

        self.shuffle_thread = threading.Thread(target=worker, args=(other_name, shuffle_params or {}), daemon=True)
        self.shuffle_thread.start()
        return True

    def _finalize_previous_round(self, prev_gid: str):
        """
        End-of-round consolidation for prev_gid:
        - Use DB current_dealt_cards (rank+suit) to:
            * Remove from undealt via nearest exact match (fallback nearest same-rank), popping from front
            * Append to dealt_cards
        - Build discarded block from rounds row in order:
            Dealer: first, second, extras (t asc)
            Seats 0..6: first, second, extras (t asc)
        - Persist undealt, dealt, discarded; clear current_dealt_cards.
        - Update in-memory shoe to keep UI consistent.
        """
        if not self.db_manager:
            return

        shoe_name = self.active_shoe_name
        try:
            state = self.db_manager.get_shoe_state(shoe_name)
            undealt = list(state.get("undealt", []))
            current = list(state.get("current", []))

            # Remove each current card from undealt with nearest exact match fallback to nearest same-rank
            def pop_front_matching(card: str):
                nonlocal undealt
                if not undealt:
                    return
                # Exact match at pointer
                if undealt[0] == card:
                    undealt.pop(0)
                    return
                idx = -1
                # nearest exact (scan forward after the pointer)
                for i in range(1, len(undealt)):
                    if undealt[i] == card:
                        idx = i
                        break
                # nearest same-rank fallback
                if idx == -1:
                    r = str(card)[0]
                    # if the pointer already matches the rank, consume it
                    if undealt and str(undealt[0])[0] == r:
                        undealt.pop(0)
                        return
                    for i in range(1, len(undealt)):
                        if str(undealt[i])[0] == r:
                            idx = i
                            break
                if idx != -1 and undealt:
                    undealt[0], undealt[idx] = undealt[idx], undealt[0]
                if undealt:
                    undealt.pop(0)

            for card in current:
                pop_front_matching(card)

            # Append current to dealt
            self.db_manager.append_dealt_cards(shoe_name, current)

            # Build discarded block for prev_gid from rounds table
            row = self.db_manager.get_round_by_game_id(shoe_name, prev_gid)
            discard_block = []

            def parse_pairs(field, allow_hidden=False):
                pairs = []
                if not field:
                    return pairs
                try:
                    raw = json.loads(field) if isinstance(field, str) else (field or [])
                    for c in raw:
                        if isinstance(c, dict):
                            v = c.get("value")
                            if v and (allow_hidden or v != "**"):
                                pairs.append((v, c.get("t", 0)))
                        elif isinstance(c, str):
                            if c and (allow_hidden or c != "**"):
                                pairs.append((c, 0))
                except Exception:
                    pass
                return pairs

            def extras_desc(pairs):
                extras = pairs[2:] if len(pairs) > 2 else []
                return sorted(extras, key=lambda x: x[1] if x[1] is not None else 0, reverse=True)

            if row:
                try:
                    # Seats 6..1: extras (t desc), then second, then first
                    for seat in range(6, 0, -1):
                        hand_idx = 5 + seat * 3
                        seat_pairs = parse_pairs(row[hand_idx] if len(row) > hand_idx else None, allow_hidden=False)
                        for v, _ in extras_desc(seat_pairs):
                            if v and v != "**":
                                discard_block.append(v)
                        if len(seat_pairs) >= 2 and seat_pairs[1][0] and seat_pairs[1][0] != "**":
                            discard_block.append(seat_pairs[1][0])
                        if len(seat_pairs) >= 1 and seat_pairs[0][0] and seat_pairs[0][0] != "**":
                            discard_block.append(seat_pairs[0][0])

                    # Seat 0: extras (t desc), then second, then first
                    seat_pairs_0 = parse_pairs(row[5] if len(row) > 5 else None, allow_hidden=False)
                    for v, _ in extras_desc(seat_pairs_0):
                        if v and v != "**":
                            discard_block.append(v)
                    if len(seat_pairs_0) >= 2 and seat_pairs_0[1][0] and seat_pairs_0[1][0] != "**":
                        discard_block.append(seat_pairs_0[1][0])
                    if len(seat_pairs_0) >= 1 and seat_pairs_0[0][0] and seat_pairs_0[0][0] != "**":
                        discard_block.append(seat_pairs_0[0][0])

                    # Dealer: extras (t desc), then second (include '**' if hidden), then first
                    dealer_pairs_raw = parse_pairs(row[3] if len(row) > 3 else None, allow_hidden=True)
                    for v, _ in extras_desc(dealer_pairs_raw):
                        if v and v != "**":
                            discard_block.append(v)
                    if len(dealer_pairs_raw) >= 2:
                        v2 = dealer_pairs_raw[1][0]
                        if v2:
                            discard_block.append(v2)  # include hidden downcard if '**'
                    if len(dealer_pairs_raw) >= 1:
                        v1 = dealer_pairs_raw[0][0]
                        if v1 and v1 != "**":
                            discard_block.append(v1)

                    self.logger.info("Successfully built discard block for round %s. Total cards: %d", prev_gid, len(discard_block))

                except Exception as e:
                    self.logger.error("Could not build discard block for round %s due to an error. "
                                     "The discard block may be empty or incomplete. Error: %s", prev_gid, e, exc_info=True)

                try:
                    self.logger.info("Discard order (pre-reverse) for round %s: first10=%s total=%d", prev_gid, discard_block[:10], len(discard_block))
                except Exception:
                    pass # Logging only, failure is not critical

            # Persist new state
            self.db_manager.replace_undealt_cards(shoe_name, undealt)
            if discard_block:
                # Reverse the round's discard block before prepending, per new requirement
                discard_block = list(reversed(discard_block))
                self.db_manager.append_discarded_cards_left(shoe_name, discard_block)
            self.db_manager.update_current_dealt_cards(shoe_name, [])

            # Update in-memory shoe to reflect DB state
            shoe = self.get_active_shoe()
            try:
                new_state = self.db_manager.get_shoe_state(shoe_name)
                if shoe:
                    shoe.undealt_cards = list(new_state.get("undealt", []))
                    shoe.dealt_cards = list(new_state.get("dealt", []))
            except Exception:
                pass

            # Track last dealt of previous round
            if current:
                self.last_dealt_card = current[-1]

            print(f"[ShoeManager] Finalized round {prev_gid}: removed {len(current)} cards, discarded {len(discard_block)} cards.")
        except Exception as e:
            print(f"[ShoeManager] _finalize_previous_round error: {e}")

    def _shuffle_worker(self, shoe_name, stack, params):
        num_iterations = int(params.get('iterations', 4))
        num_chunks = int(params.get('chunks', 8))
        # Optional seed can be passed in params for deterministic testing
        seed = params.get('seed')
        shuffled_deck = perform_full_shuffle(stack, num_iterations, num_chunks, seed=seed)
        
        new_shoe = Shoe()
        new_shoe.undealt_cards = list(shuffled_deck)
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
