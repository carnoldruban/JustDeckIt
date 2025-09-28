"""
Production-Ready Infinity Blackjack Assistant
Captures live game data with robust error handling and performance optimization
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import threading
from queue import Queue, Empty
import signal

# Third-party imports
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    print("ERROR: Selenium not installed. Run: pip install selenium webdriver-manager")
    SELENIUM_AVAILABLE = False
    sys.exit(1)

import websockets
import requests
from collections import deque
import statistics

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('infinity_assistant.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===================== Configuration =====================

@dataclass
class Config:
    """Central configuration for the assistant"""
    # Browser settings
    headless: bool = False
    window_size: Tuple[int, int] = (1920, 1080)
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    
    # Timing settings (in seconds)
    page_load_timeout: int = 30
    element_wait_timeout: int = 10
    polling_interval: float = 0.5
    action_delay: float = 1.0  # Delay between actions to appear human
    
    # Data capture settings
    capture_duration_hours: float = 1.0
    data_directory: str = "captured_data"
    save_interval: int = 60  # Save data every N seconds
    
    # Performance settings
    max_memory_mb: int = 500
    max_history_size: int = 1000
    
    # Casino configurations
    casinos: Dict = field(default_factory=lambda: {
        "draftkings": {
            "url": "https://casino.draftkings.com",
            "game_path": "/games/evolution-infinite-blackjack",
            "iframe_selector": "iframe[src*='evo-games.com']"
        },
        "betmgm": {
            "url": "https://casino.betmgm.com",
            "game_path": "/en/games/infinite-blackjack",
            "iframe_selector": "iframe[src*='evo-games.com']"
        },
        "fanduel": {
            "url": "https://casino.fanduel.com",
            "game_path": "/games/infinite-blackjack",
            "iframe_selector": "iframe[src*='evo-games.com']"
        }
    })

# ===================== Data Models =====================

class GamePhase(Enum):
    WAITING = "waiting"
    BETTING = "betting"
    DEALING = "dealing"
    PLAYER_TURN = "player_turn"
    DEALER_TURN = "dealer_turn"
    RESOLVING = "resolving"
    FINISHED = "finished"

class Action(Enum):
    HIT = "hit"
    STAND = "stand"
    DOUBLE = "double"
    SPLIT = "split"
    INSURANCE = "insurance"
    NONE = "none"

@dataclass
class Card:
    rank: str
    suit: str
    
    @property
    def value(self) -> int:
        if self.rank == 'A':
            return 11
        elif self.rank in ['K', 'Q', 'J']:
            return 10
        else:
            try:
                return int(self.rank)
            except:
                return 0

@dataclass
class GameState:
    """Complete game state at a point in time"""
    timestamp: float
    game_id: Optional[str]
    phase: GamePhase
    player_cards: List[Card]
    dealer_cards: List[Card]
    player_total: int
    dealer_total: int
    is_soft: bool
    available_actions: List[Action]
    balance: float
    bet_amount: float
    win_amount: float
    players_online: int
    raw_dom_data: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp,
            'game_id': self.game_id,
            'phase': self.phase.value,
            'player_cards': [{'rank': c.rank, 'suit': c.suit} for c in self.player_cards],
            'dealer_cards': [{'rank': c.rank, 'suit': c.suit} for c in self.dealer_cards],
            'player_total': self.player_total,
            'dealer_total': self.dealer_total,
            'is_soft': self.is_soft,
            'available_actions': [a.value for a in self.available_actions],
            'balance': self.balance,
            'bet_amount': self.bet_amount,
            'win_amount': self.win_amount,
            'players_online': self.players_online
        }

@dataclass
class SessionStats:
    """Statistics for the current session"""
    hands_played: int = 0
    hands_won: int = 0
    hands_lost: int = 0
    hands_pushed: int = 0
    total_wagered: float = 0.0
    total_won: float = 0.0
    start_balance: float = 0.0
    current_balance: float = 0.0
    peak_balance: float = 0.0
    lowest_balance: float = 0.0
    session_start: float = field(default_factory=time.time)
    
    @property
    def win_rate(self) -> float:
        if self.hands_played == 0:
            return 0.0
        return (self.hands_won / self.hands_played) * 100
    
    @property
    def roi(self) -> float:
        if self.total_wagered == 0:
            return 0.0
        return ((self.total_won - self.total_wagered) / self.total_wagered) * 100

# ===================== DOM Selectors =====================

class Selectors:
    """Evolution Gaming DOM selectors - Production tested"""
    
    # Card selectors with fallbacks
    PLAYER_CARDS = [
        "div[data-role='player-cards'] .card",
        ".playerCardsContainer .playingCard",
        ".player-hand .card-wrapper",
        "div.player-cards .card"
    ]
    
    DEALER_CARDS = [
        "div[data-role='dealer-cards'] .card",
        ".dealerCardsContainer .playingCard",
        ".dealer-hand .card-wrapper",
        "div.dealer-cards .card"
    ]
    
    # Score displays
    PLAYER_SCORE = [
        "div[data-role='player-score']",
        ".playerScore",
        ".player-total",
        "span.hand-value.player"
    ]
    
    DEALER_SCORE = [
        "div[data-role='dealer-score']",
        ".dealerScore",
        ".dealer-total",
        "span.hand-value.dealer"
    ]
    
    # Action buttons
    ACTIONS = {
        'hit': ["button[data-action='hit']", ".hit-button", "#hitButton"],
        'stand': ["button[data-action='stand']", ".stand-button", "#standButton"],
        'double': ["button[data-action='double']", ".double-button", "#doubleButton"],
        'split': ["button[data-action='split']", ".split-button", "#splitButton"],
        'insurance': ["button[data-action='insurance']", ".insurance-button"]
    }
    
    # Game info
    BALANCE = ["div[data-role='balance']", ".balance-value", ".player-balance"]
    BET_AMOUNT = ["div[data-role='total-bet']", ".totalBet", ".current-bet"]
    WIN_AMOUNT = ["div[data-role='win-amount']", ".winAmount", ".last-win"]
    GAME_PHASE = ["div[data-role='game-phase']", ".gamePhase", ".game-status"]
    PLAYERS_ONLINE = ["div.playersOnline", ".online-players", ".player-count"]

# ===================== Core Engine =====================

class InfinityAssistant:
    """Production-ready Infinity Blackjack Assistant"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.driver = None
        self.session_stats = SessionStats()
        self.game_history = deque(maxlen=self.config.max_history_size)
        self.data_queue = Queue()
        self.is_running = False
        self.capture_thread = None
        self.save_thread = None
        
        # Setup data directory
        self.data_dir = Path(self.config.data_directory)
        self.data_dir.mkdir(exist_ok=True)
        
        # Session ID for data files
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        logger.info(f"Initialized Infinity Assistant - Session: {self.session_id}")
    
    def setup_driver(self) -> bool:
        """Setup Chrome driver with production settings"""
        try:
            options = Options()
            
            # Anti-detection settings
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument(f'user-agent={self.config.user_agent}')
            
            # Performance settings
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-logging')
            options.add_argument('--log-level=3')
            
            # Window settings
            if self.config.headless:
                options.add_argument('--headless=new')
            options.add_argument(f'--window-size={self.config.window_size[0]},{self.config.window_size[1]}')
            
            # Create driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Set timeouts
            self.driver.set_page_load_timeout(self.config.page_load_timeout)
            self.driver.implicitly_wait(self.config.element_wait_timeout)
            
            # Override navigator.webdriver
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            """)
            
            logger.info("Chrome driver setup successful")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup driver: {e}")
            return False
    
    def navigate_to_game(self, casino: str = "draftkings") -> bool:
        """Navigate to the Infinity Blackjack game"""
        try:
            casino_config = self.config.casinos.get(casino)
            if not casino_config:
                logger.error(f"Unknown casino: {casino}")
                return False
            
            # Navigate to casino
            url = casino_config['url'] + casino_config['game_path']
            logger.info(f"Navigating to {url}")
            self.driver.get(url)
            
            # Wait for and switch to iframe
            logger.info("Waiting for Evolution Gaming iframe...")
            iframe = WebDriverWait(self.driver, self.config.page_load_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, casino_config['iframe_selector']))
            )
            
            self.driver.switch_to.frame(iframe)
            logger.info("Successfully entered Evolution Gaming iframe")
            
            # Wait for game to initialize
            time.sleep(3)
            
            return True
            
        except TimeoutException:
            logger.error("Timeout waiting for game to load")
            return False
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return False
    
    def extract_card(self, element) -> Optional[Card]:
        """Extract card information with multiple fallback methods"""
        try:
            rank = None
            suit = None
            
            # Method 1: Data attributes
            rank = element.get_attribute('data-rank') or element.get_attribute('data-value')
            suit = element.get_attribute('data-suit') or element.get_attribute('data-color')
            
            # Method 2: Class parsing
            if not rank:
                classes = element.get_attribute('class') or ''
                # Look for patterns like 'card-10H', 'rank-A', etc.
                import re
                
                # Try to find rank
                rank_match = re.search(r'(?:card-|rank-)([AKQJ2-9]|10)', classes)
                if rank_match:
                    rank = rank_match.group(1)
                
                # Try to find suit
                suit_match = re.search(r'(?:suit-|[^a-z])([HDCS]|hearts|diamonds|clubs|spades)', classes, re.I)
                if suit_match:
                    suit = suit_match.group(1)
            
            # Method 3: Inner text/elements
            if not rank:
                try:
                    rank_elem = element.find_element(By.CSS_SELECTOR, ".rank, .card-rank, [data-rank]")
                    rank = rank_elem.text or rank_elem.get_attribute('data-rank')
                except:
                    pass
            
            # Method 4: Image/background analysis
            if not rank:
                style = element.get_attribute('style') or ''
                bg_image = element.value_of_css_property('background-image') or ''
                
                # Look for card codes in image URLs
                for text in [style, bg_image]:
                    match = re.search(r'/([AKQJ2-9]|10)([HDCS])', text)
                    if match:
                        rank = match.group(1)
                        suit = match.group(2)
                        break
            
            # Normalize suit names
            if suit:
                suit_map = {
                    'H': 'hearts', 'D': 'diamonds', 
                    'C': 'clubs', 'S': 'spades'
                }
                suit = suit_map.get(suit, suit).lower()
            
            if rank:
                return Card(rank=rank.upper(), suit=suit or 'unknown')
            
            return None
            
        except Exception as e:
            logger.debug(f"Card extraction error: {e}")
            return None
    
    def get_element_safely(self, selectors: List[str], multiple: bool = False):
        """Safely get element(s) with fallback selectors"""
        for selector in selectors:
            try:
                if multiple:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        return elements
                else:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element and element.is_displayed():
                        return element
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return [] if multiple else None
    
    def extract_game_state(self) -> Optional[GameState]:
        """Extract complete game state from DOM"""
        try:
            # Extract cards
            player_cards = []
            player_elements = self.get_element_safely(Selectors.PLAYER_CARDS, multiple=True)
            for elem in player_elements:
                card = self.extract_card(elem)
                if card:
                    player_cards.append(card)
            
            dealer_cards = []
            dealer_elements = self.get_element_safely(Selectors.DEALER_CARDS, multiple=True)
            for elem in dealer_elements:
                card = self.extract_card(elem)
                if card:
                    dealer_cards.append(card)
            
            # Extract scores
            player_total = 0
            player_score_elem = self.get_element_safely(Selectors.PLAYER_SCORE)
            if player_score_elem:
                try:
                    player_total = int(''.join(c for c in player_score_elem.text if c.isdigit()))
                except:
                    player_total = self.calculate_hand_total(player_cards)
            else:
                player_total = self.calculate_hand_total(player_cards)
            
            dealer_total = 0
            dealer_score_elem = self.get_element_safely(Selectors.DEALER_SCORE)
            if dealer_score_elem:
                try:
                    dealer_total = int(''.join(c for c in dealer_score_elem.text if c.isdigit()))
                except:
                    dealer_total = self.calculate_hand_total(dealer_cards)
            else:
                dealer_total = self.calculate_hand_total(dealer_cards)
            
            # Check available actions
            available_actions = []
            for action, selectors in Selectors.ACTIONS.items():
                button = self.get_element_safely(selectors)
                if button and button.is_enabled():
                    available_actions.append(Action(action))
            
            # Extract game info
            balance = self.extract_float(self.get_element_safely(Selectors.BALANCE))
            bet_amount = self.extract_float(self.get_element_safely(Selectors.BET_AMOUNT))
            win_amount = self.extract_float(self.get_element_safely(Selectors.WIN_AMOUNT))
            
            # Extract game phase
            phase = GamePhase.WAITING
            if available_actions:
                if Action.HIT in available_actions:
                    phase = GamePhase.PLAYER_TURN
                else:
                    phase = GamePhase.BETTING
            elif dealer_total > 0 and player_total > 0:
                phase = GamePhase.DEALER_TURN
            
            # Extract player count
            players_online = 0
            players_elem = self.get_element_safely(Selectors.PLAYERS_ONLINE)
            if players_elem:
                try:
                    players_online = int(''.join(c for c in players_elem.text if c.isdigit()))
                except:
                    pass
            
            # Check if hand is soft
            is_soft = self.is_hand_soft(player_cards, player_total)
            
            # Generate game ID
            game_id = f"{int(time.time())}_{len(self.game_history)}"
            
            return GameState(
                timestamp=time.time(),
                game_id=game_id,
                phase=phase,
                player_cards=player_cards,
                dealer_cards=dealer_cards,
                player_total=player_total,
                dealer_total=dealer_total,
                is_soft=is_soft,
                available_actions=available_actions,
                balance=balance,
                bet_amount=bet_amount,
                win_amount=win_amount,
                players_online=players_online
            )
            
        except Exception as e:
            logger.error(f"State extraction error: {e}")
            return None
    
    def calculate_hand_total(self, cards: List[Card]) -> int:
        """Calculate blackjack hand total"""
        total = 0
        aces = 0
        
        for card in cards:
            if card.rank == 'A':
                aces += 1
                total += 11
            elif card.rank in ['K', 'Q', 'J']:
                total += 10
            else:
                try:
                    total += int(card.rank)
                except:
                    pass
        
        # Adjust for aces
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        
        return total
    
    def is_hand_soft(self, cards: List[Card], total: int) -> bool:
        """Check if hand is soft"""
        has_ace = any(card.rank == 'A' for card in cards)
        return has_ace and total <= 21
    
    def extract_float(self, element) -> float:
        """Extract float value from element text"""
        if not element:
            return 0.0
        try:
            text = element.text
            # Remove currency symbols and non-numeric characters
            cleaned = ''.join(c for c in text if c.isdigit() or c == '.')
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0
    
    def capture_loop(self):
        """Main capture loop running in separate thread"""
        logger.info("Starting capture loop")
        last_state = None
        state_changes = 0
        
        capture_end_time = time.time() + (self.config.capture_duration_hours * 3600)
        
        while self.is_running and time.time() < capture_end_time:
            try:
                # Extract current state
                state = self.extract_game_state()
                
                if state:
                    # Check if state changed
                    if not last_state or self.state_changed(state, last_state):
                        state_changes += 1
                        
                        # Update session stats
                        self.update_session_stats(state, last_state)
                        
                        # Add to history
                        self.game_history.append(state)
                        
                        # Queue for saving
                        self.data_queue.put(state)
                        
                        # Log summary
                        logger.info(f"State #{state_changes}: "
                                  f"Player: {state.player_total}, "
                                  f"Dealer: {state.dealer_total}, "
                                  f"Phase: {state.phase.value}, "
                                  f"Actions: {[a.value for a in state.available_actions]}")
                        
                        last_state = state
                
                # Sleep before next poll
                time.sleep(self.config.polling_interval)
                
            except Exception as e:
                logger.error(f"Capture loop error: {e}")
                time.sleep(1)
        
        logger.info(f"Capture completed. Total state changes: {state_changes}")
    
    def state_changed(self, new_state: GameState, old_state: GameState) -> bool:
        """Check if game state has meaningfully changed"""
        if not old_state:
            return True
        
        # Check key differences
        if new_state.phase != old_state.phase:
            return True
        if len(new_state.player_cards) != len(old_state.player_cards):
            return True
        if len(new_state.dealer_cards) != len(old_state.dealer_cards):
            return True
        if new_state.player_total != old_state.player_total:
            return True
        if new_state.dealer_total != old_state.dealer_total:
            return True
        if new_state.available_actions != old_state.available_actions:
            return True
        
        return False
    
    def update_session_stats(self, state: GameState, prev_state: Optional[GameState]):
        """Update session statistics"""
        if not prev_state:
            self.session_stats.start_balance = state.balance
            self.session_stats.current_balance = state.balance
            self.session_stats.peak_balance = state.balance
            self.session_stats.lowest_balance = state.balance
            return
        
        # Update balance tracking
        self.session_stats.current_balance = state.balance
        self.session_stats.peak_balance = max(self.session_stats.peak_balance, state.balance)
        self.session_stats.lowest_balance = min(self.session_stats.lowest_balance, state.balance)
        
        # Check for completed hands
        if prev_state.phase in [GamePhase.PLAYER_TURN, GamePhase.DEALER_TURN] and \
           state.phase in [GamePhase.FINISHED, GamePhase.BETTING]:
            self.session_stats.hands_played += 1
            
            # Determine outcome
            if state.win_amount > 0:
                if state.win_amount > prev_state.bet_amount:
                    self.session_stats.hands_won += 1
                else:
                    self.session_stats.hands_pushed += 1
            else:
                self.session_stats.hands_lost += 1
            
            # Update wagering stats
            self.session_stats.total_wagered += prev_state.bet_amount
            self.session_stats.total_won += state.win_amount
    
    def save_loop(self):
        """Background thread for saving captured data"""
        logger.info("Starting save loop")
        buffer = []
        last_save = time.time()
        
        while self.is_running or not self.data_queue.empty():
            try:
                # Get data from queue (with timeout)
                try:
                    state = self.data_queue.get(timeout=1)
                    buffer.append(state.to_dict())
                except Empty:
                    pass
                
                # Save periodically or when buffer is large
                if (time.time() - last_save > self.config.save_interval or 
                    len(buffer) >= 100):
                    
                    if buffer:
                        self.save_data(buffer)
                        buffer.clear()
                        last_save = time.time()
                
            except Exception as e:
                logger.error(f"Save loop error: {e}")
        
        # Final save
        if buffer:
            self.save_data(buffer)
        
        logger.info("Save loop completed")
    
    def save_data(self, data: List[Dict]):
        """Save captured data to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.data_dir / f"capture_{self.session_id}_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump({
                    'session_id': self.session_id,
                    'timestamp': time.time(),
                    'casino': 'Evolution Gaming Infinity Blackjack',
                    'statistics': asdict(self.session_stats),
                    'data': data
                }, f, indent=2)
            
            logger.info(f"Saved {len(data)} states to {filename}")
            
        except Exception as e:
            logger.error(f"Save error: {e}")
    
    def start_capture(self, casino: str = "draftkings"):
        """Start the capture process"""
        logger.info(f"Starting capture for {self.config.capture_duration_hours} hours")
        
        # Setup driver
        if not self.setup_driver():
            logger.error("Failed to setup driver")
            return False
        
        # Navigate to game
        if not self.navigate_to_game(casino):
            logger.error("Failed to navigate to game")
            return False
        
        # Start threads
        self.is_running = True
        
        self.capture_thread = threading.Thread(target=self.capture_loop, daemon=True)
        self.capture_thread.start()
        
        self.save_thread = threading.Thread(target=self.save_loop, daemon=True)
        self.save_thread.start()
        
        logger.info("Capture started successfully")
        return True
    
    def stop_capture(self):
        """Stop the capture process"""
        logger.info("Stopping capture...")
        self.is_running = False
        
        # Wait for threads to complete
        if self.capture_thread:
            self.capture_thread.join(timeout=5)
        if self.save_thread:
            self.save_thread.join(timeout=10)
        
        # Close driver
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        # Save final statistics
        self.save_final_report()
        
        logger.info("Capture stopped")
    
    def save_final_report(self):
        """Save final session report"""
        try:
            report = {
                'session_id': self.session_id,
                'duration_hours': self.config.capture_duration_hours,
                'total_states_captured': len(self.game_history),
                'statistics': {
                    'hands_played': self.session_stats.hands_played,
                    'hands_won': self.session_stats.hands_won,
                    'hands_lost': self.session_stats.hands_lost,
                    'hands_pushed': self.session_stats.hands_pushed,
                    'win_rate': f"{self.session_stats.win_rate:.2f}%",
                    'total_wagered': self.session_stats.total_wagered,
                    'total_won': self.session_stats.total_won,
                    'roi': f"{self.session_stats.roi:.2f}%",
                    'start_balance': self.session_stats.start_balance,
                    'final_balance': self.session_stats.current_balance,
                    'peak_balance': self.session_stats.peak_balance,
                    'lowest_balance': self.session_stats.lowest_balance,
                    'session_duration': time.time() - self.session_stats.session_start
                }
            }
            
            filename = self.data_dir / f"report_{self.session_id}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Final report saved to {filename}")
            
            # Print summary
            print("\n" + "="*50)
            print("SESSION SUMMARY")
            print("="*50)
            print(f"Duration: {self.config.capture_duration_hours} hours")
            print(f"States Captured: {len(self.game_history)}")
            print(f"Hands Played: {self.session_stats.hands_played}")
            print(f"Win Rate: {self.session_stats.win_rate:.2f}%")
            print(f"ROI: {self.session_stats.roi:.2f}%")
            print("="*50)
            
        except Exception as e:
            logger.error(f"Failed to save final report: {e}")

# ===================== Main Application =====================

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Shutdown signal received")
    if 'assistant' in globals():
        assistant.stop_capture()
    sys.exit(0)

def main():
    """Main entry point"""
    print("="*60)
    print("INFINITY BLACKJACK ASSISTANT - PRODUCTION")
    print("="*60)
    print("Capture Mode: 1 Hour Live Data Collection")
    print("-"*60)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get configuration
    casino = input("Enter casino (draftkings/betmgm/fanduel) [draftkings]: ").strip() or "draftkings"
    headless = input("Run headless? (y/n) [n]: ").strip().lower() == 'y'
    
    # Create configuration
    config = Config(
        headless=headless,
        capture_duration_hours=1.0,  # 1 hour capture
        polling_interval=0.5,  # Check every 500ms
        save_interval=60  # Save every minute
    )
    
    # Create and start assistant
    global assistant
    assistant = InfinityAssistant(config)
    
    print("\n" + "="*60)
    print("Starting 1-hour capture session...")
    print("Press Ctrl+C to stop early")
    print("="*60 + "\n")
    
    if assistant.start_capture(casino):
        try:
            # Wait for capture to complete
            assistant.capture_thread.join()
            assistant.stop_capture()
        except KeyboardInterrupt:
            print("\n\nStopping capture...")
            assistant.stop_capture()
    else:
        print("Failed to start capture")
        sys.exit(1)

if __name__ == "__main__":
    main()
