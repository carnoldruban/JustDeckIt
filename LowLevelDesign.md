# Infinity Blackjack Assistant - Low Level Design

## Module Specifications

### 1. HTML Parser Module (`html_parser.py`)

#### Class: InfinityBJParser
```python
class InfinityBJParser:
    def parse_html(self, html_content: str) -> GameState
    def extract_game_phase(self, soup: BeautifulSoup) -> str
    def extract_player_data(self, soup: BeautifulSoup) -> PlayerData
    def extract_dealer_data(self, soup: BeautifulSoup) -> DealerData
    def extract_betting_info(self, soup: BeautifulSoup) -> BettingInfo
    def extract_winners_data(self, soup: BeautifulSoup) -> List[Winner]
```

#### Key Methods:
- **parse_html()**: Main entry point, returns complete GameState
- **extract_game_phase()**: Identifies betting/playing/results phase
- **extract_player_data()**: Gets balance, cards, score
- **extract_dealer_data()**: Gets dealer cards and score
- **extract_betting_info()**: Parses bet amounts and side bets
- **extract_winners_data()**: Processes winners list and payouts

### 2. Game State Module (`game_state.py`)

#### Data Classes:
```python
@dataclass
class PlayerData:
    balance: float
    total_bet: float
    cards: List[Card]
    score: int
    decision: str

@dataclass
class DealerData:
    visible_card: Card
    hidden_card: Optional[Card]
    score: int

@dataclass
class BettingInfo:
    main_bet: float
    side_bets: Dict[str, float]
    available_chips: List[int]
    bet_limits: Dict[str, Tuple[int, int]]

@dataclass
class GameState:
    timestamp: datetime
    phase: str
    player: PlayerData
    dealer: DealerData
    betting: BettingInfo
    winners: List[Winner]
    player_count: int
```

### 3. Strategy Engine Module (`strategy_engine.py`)

#### Class: InfinityBJStrategy
```python
class InfinityBJStrategy:
    def get_basic_strategy(self, player_total: int, dealer_card: int) -> str
    def calculate_bet_recommendation(self, balance: float, count: int) -> float
    def analyze_side_bets(self, betting_info: BettingInfo) -> Dict[str, bool]
    def get_bankroll_advice(self, current_balance: float, session_data: List[GameState]) -> str
```

#### Strategy Tables:
- Basic strategy matrix for infinity blackjack
- Side bet probability calculations
- Bankroll management rules
- Risk assessment algorithms

### 4. Database Module (`database.py`)

#### Class: InfinityBJDatabase
```python
class InfinityBJDatabase:
    def create_tables(self) -> None
    def insert_game_state(self, state: GameState) -> int
    def get_session_history(self, session_id: str) -> List[GameState]
    def get_performance_stats(self, date_range: Tuple[datetime, datetime]) -> Dict
    def update_balance_tracking(self, balance: float, timestamp: datetime) -> None
```

#### Database Schema:
```sql
-- Game sessions table
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    starting_balance REAL,
    ending_balance REAL
);

-- Game states table
CREATE TABLE game_states (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    timestamp TIMESTAMP,
    phase TEXT,
    player_balance REAL,
    player_bet REAL,
    player_cards TEXT,
    player_score INTEGER,
    dealer_visible_card TEXT,
    dealer_score INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions (id)
);

-- Betting history table
CREATE TABLE betting_history (
    id INTEGER PRIMARY KEY,
    game_state_id INTEGER,
    bet_type TEXT,
    bet_amount REAL,
    outcome TEXT,
    payout REAL,
    FOREIGN KEY (game_state_id) REFERENCES game_states (id)
);
```

### 5. User Interface Module (`ui_dashboard.py`)

#### Class: InfinityBJDashboard
```python
class InfinityBJDashboard:
    def __init__(self, controller: GameController)
    def create_main_window(self) -> None
    def update_game_display(self, state: GameState) -> None
    def show_strategy_recommendation(self, recommendation: str) -> None
    def display_balance_tracking(self, balance_history: List[float]) -> None
    def show_alerts(self, alert_type: str, message: str) -> None
```

#### UI Components:
- **Game State Panel**: Current cards, scores, phase
- **Strategy Panel**: Recommendations and advice
- **Balance Panel**: Current balance and session P&L
- **Statistics Panel**: Win rate, average bet, session stats
- **Alerts Panel**: Important notifications and warnings

### 6. Controller Module (`controller.py`)

#### Class: GameController
```python
class GameController:
    def __init__(self)
    def process_html_input(self, html: str) -> None
    def start_session(self) -> str
    def end_session(self) -> SessionSummary
    def get_current_recommendation(self) -> str
    def export_session_data(self, format: str) -> str
```

#### Process Flow:
1. **HTML Input** → Parse → Validate → Store
2. **State Change** → Strategy Analysis → UI Update
3. **User Action** → Log Decision → Update Database
4. **Session End** → Generate Summary → Export Data

## Error Handling Strategy

### Exception Hierarchy:
```python
class InfinityBJError(Exception): pass
class ParseError(InfinityBJError): pass
class DatabaseError(InfinityBJError): pass
class StrategyError(InfinityBJError): pass
class UIError(InfinityBJError): pass
```

### Error Recovery:
- **Parse Errors**: Retry with fallback patterns
- **Database Errors**: Queue operations, retry on reconnect
- **Strategy Errors**: Use basic strategy as fallback
- **UI Errors**: Log error, continue with reduced functionality

## Performance Optimization

### Parsing Optimization:
- Pre-compiled regex patterns
- Selective DOM parsing
- Caching of repeated elements

### Database Optimization:
- Indexed columns for fast queries
- Batch inserts for bulk operations
- Connection pooling for concurrent access

### Memory Management:
- Lazy loading of historical data
- Periodic cleanup of old sessions
- Efficient data structures for real-time processing

## Configuration Management

### Config File Structure:
```ini
[database]
path = infinity_bj.db
backup_interval = 3600

[parsing]
timeout = 5
retry_attempts = 3

[strategy]
basic_strategy_file = basic_strategy.json
bankroll_percentage = 0.02

[ui]
update_interval = 100
theme = dark
```

## Logging Strategy

### Log Levels:
- **DEBUG**: Detailed parsing information
- **INFO**: Game state changes, user actions
- **WARNING**: Recoverable errors, unusual patterns
- **ERROR**: Unrecoverable errors, system failures
- **CRITICAL**: System shutdown events

### Log Format:
```
[TIMESTAMP] [LEVEL] [MODULE] [SESSION_ID] MESSAGE
```