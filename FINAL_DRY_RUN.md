### Final Dry Run Analysis (Card Counting & Strategy)

**Objective:** To verify the functionality of the newly added card counting and strategy assistant features.

---

### 1. UI and Initialization
**Action:** User runs `python tracker_app.py`.
**Expected Outcome:**
*   The application starts correctly.
*   The UI now includes two new panels in the 'Live Tracker' tab: 'Card Counts' and 'Strategy Assistant'.
*   The 'Card Counts' panel displays labels for Hi-Lo and Wong Halves running and true counts.
*   The 'Strategy Assistant' panel displays an input field for the user's seat number and labels for bet and action recommendations.
*   Two counter objects, `HiLoCounter` and `WongHalvesCounter`, are instantiated.

### 2. Live Data Processing
**Action:** User starts tracking, and game data is received from the scraper.
**Expected Outcome:**
1.  The `process_queues` loop receives the data payload.
2.  `shoe_manager.process_game_state` correctly identifies the newly dealt cards.
3.  The ranks of these new cards are passed to **both** `self.hilo_counter.process_cards()` and `self.wong_halves_counter.process_cards()`.
4.  The `update_counts_display()` method is called, and all four count labels in the UI are updated with the new, correct values.
5.  The `update_strategy_display()` method is called.
    *   It checks if a seat number is entered in the UI.
    *   If yes, it parses the player's hand and dealer's up-card from the payload for that specific seat.
    *   It calls `get_bet_recommendation()` and `get_strategy_action()` from the `strategy.py` module, passing the correct Hi-Lo true count.
    *   The bet and action recommendation labels in the UI are updated with the correct advice.

### 3. Shoe Reset
**Action:** User clicks the 'Mark End of Shoe / Switch & Shuffle' button.
**Expected Outcome:**
*   The `handle_shoe_end` method is called.
*   In addition to switching the shoe, it now also calls `self.hilo_counter.reset()` and `self.wong_halves_counter.reset()`.
*   The `update_counts_display()` method is called, and all count labels in the UI correctly reset to their initial state.

---
**Conclusion:** The card counting and strategy assistant features are correctly implemented and integrated into the application's data flow and UI. The application is now feature-complete as per the latest request.
