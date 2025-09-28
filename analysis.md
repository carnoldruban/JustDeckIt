# Infinity Blackjack HTML Analysis

## Files Analyzed: root_div_5.html & root_div_10.html

### Key Findings:

**Game State:**
- Both files show "NEXT GAME SOON" status
- Player balance: $10.67
- Total bet: $0 (no active bets)

**Player Hand:**
- Score: 13
- Cards: 4♠, 6♠, 3♦ (3 cards total)
- Decision: STAND (indicated by decision icon)

**Dealer Hand:**
- Visible card: Q♦ (Queen of Diamonds)
- Hidden card: Face down
- Dealer score: 10

**Side Bets Available:**
- HOT 3: Pays if first two cards + dealer upcard total 19-21 (2x multiplier shown)
- 21+3: Suited trips, flush, straight, three of a kind
- PERFECT PAIRS: Pays if first two cards are a pair
- BUST IT: Pays if dealer busts

**Betting Limits:**
- Main bet: $1-5,000
- Side bets: $1-250 (Hot 3, 21+3, Perfect Pairs)
- Bust It: $1-100

**Player Count:**
- File 1: 67 players
- File 2: 21 players (significant drop)

**UI Elements:**
- Chip denominations: 1, 2, 5, 25, 100, 500
- Selected chip: $1
- Undo/Double buttons disabled
- Chat functionality active

## Files Analyzed: root_div_15.html & root_div_20.html

### Key Changes from Previous Files:

**Game State Progression:**
- File 15: Player count increased to 124 (from 21)
- File 15: Result shows "Hit" decision icon
- File 20: Same player count (124), Result shows "Bust" icon
- Chat message changed: "İ want married with you"

**Game Flow Observation:**
- Same hand configuration maintained: 4♠, 6♠, 3♦ = 13
- Same dealer upcard: Q♦ (10 value)
- Progression from "Stand" → "Hit" → "Bust" suggests player took additional card and busted
- This indicates the game captures different decision points in the same round

**UI Consistency:**
- Balance remains: $10.67
- Total bet remains: $0
- Same side bet availability and limits
- Same chip denominations and selection ($1 selected)
- "NEXT GAME SOON" status maintained

## Files Analyzed: root_div_25.html & root_div_30.html

### Key Changes from Previous Files:

**Game State Progression:**
- File 25: No chat messages visible (empty message container)
- File 25: Status shows "PLACE YOUR BETS" with betting timer active
- File 25: Tooltip visible showing "21+3" bet explanation
- File 30: Same betting phase status maintained
- File 30: No chat messages visible (consistent with file 25)

**UI State Observations:**
- Both files show active betting phase (not "NEXT GAME SOON")
- Timer is visible and active in both files
- Main bet spot shows enabled state with spinning border animation
- Side bet spots remain disabled
- Same balance ($10.67) and total bet ($0) maintained
- Same chip denominations available (1, 2, 5 enabled; 25, 100, 500 disabled)

**Winners List Consistency:**
- Same 42 winners with total winnings of $497
- Identical winner amounts and usernames across both files
- Winners list animation continues (transform: translate3d(0px, -900px, 0px))

**Game Flow Analysis:**
- These files appear to capture the betting phase of a new round
- Transition from "NEXT GAME SOON" (previous files) to "PLACE YOUR BETS" (current files)
- No player cards or dealer cards visible - pure betting interface
- All side bets information panel available but bets disabled

### Analysis Progress: 6/25 files completed