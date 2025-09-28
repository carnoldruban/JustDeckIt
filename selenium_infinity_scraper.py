"""
Selenium-based Infinity Blackjack Scraper
Direct iframe access using Selenium WebDriver
Works across multiple casino sites with Evolution Gaming tables
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from strategy_engine import InfinityStrategyEngine, Action

@dataclass
class GameState:
    player_cards: List[Dict]
    dealer_cards: List[Dict]
    player_total: int
    dealer_total: int
    is_soft: bool
    can_hit: bool
    can_stand: bool
    can_double: bool
    can_split: bool
    balance: float
    bet_amount: float
    game_status: str
    timestamp: int

class SeleniumInfinityScraper:
    """
    Selenium-based scraper that can directly access iframe content
    """
    
    def __init__(self, casino_site: str = "draftkings", headless: bool = False):
        self.casino_site = casino_site
        self.driver = None
        self.strategy_engine = InfinityStrategyEngine()
        self.game_state_history = []
        
        # Casino site configurations
        self.casino_configs = {
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
        }
        
        # Evolution Gaming iframe selectors (these are consistent across sites)
        self.selectors = {
            # Card selectors - Evolution Gaming specific
            'player_cards': 'div[data-role="player-cards"] div.card',
            'dealer_cards': 'div[data-role="dealer-cards"] div.card',
            'common_cards': 'div[data-role="common-cards"] div.card',
            
            # Alternative card selectors (if above don't work)
            'alt_player_cards': '.playerCards .playingCard',
            'alt_dealer_cards': '.dealerCards .playingCard',
            
            # Card value extractors
            'card_rank': 'span.rank, div.rank',
            'card_suit': 'span.suit, div.suit',
            
            # Score displays
            'player_score': 'div[data-role="player-score"], .playerScore',
            'dealer_score': 'div[data-role="dealer-score"], .dealerScore',
            
            # Action buttons
            'hit_button': 'button[data-action="hit"], button.hit-button',
            'stand_button': 'button[data-action="stand"], button.stand-button',
            'double_button': 'button[data-action="double"], button.double-button',
            'split_button': 'button[data-action="split"], button.split-button',
            
            # Game status
            'game_phase': 'div[data-role="game-phase"], .gamePhase',
            'bet_timer': 'div.betTimer, div[data-role="timer"]',
            'decision_timer': 'div.decisionTimer',
            
            # Balance and betting
            'balance': 'div[data-role="balance"], .balance-value',
            'total_bet': 'div[data-role="total-bet"], .totalBet',
            'chip_selector': 'div.chip-selector button',
            
            # Results
            'result_message': 'div[data-role="result"], .resultMessage',
            'win_amount': 'div[data-role="win-amount"], .winAmount',
            
            # Infinity specific
            'players_online': 'div.playersOnline, span.online-players',
            'your_seat': 'div.yourSeat, div[data-role="your-seat"]'
        }
        
        self.setup_driver(headless)
    
    def setup_driver(self, headless: bool = False):
        """Setup Chrome driver with optimal settings"""
        chrome_options = Options()
        
        # Essential options
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Performance options
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Headless mode if requested
        if headless:
            chrome_options.add_argument('--headless')
        
        # Window size for consistency
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Create driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Override navigator.webdriver flag
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def navigate_to_game(self) -> bool:
        """Navigate to the Infinity Blackjack game"""
        try:
            config = self.casino_configs.get(self.casino_site)
            if not config:
                print(f"❌ Unknown casino site: {self.casino_site}")
                return False
            
            # Navigate to casino
            print(f"🎰 Navigating to {config['url']}")
            self.driver.get(config['url'] + config['game_path'])
            
            # Wait for page load
            time.sleep(5)
            
            # Wait for iframe to load
            print("⏳ Waiting for Evolution Gaming iframe...")
            iframe = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, config['iframe_selector']))
            )
            
            # Switch to iframe
            self.driver.switch_to.frame(iframe)
            print("✅ Successfully entered Evolution Gaming iframe")
            
            # Wait for game to fully load
            time.sleep(3)
            
            return True
            
        except TimeoutException:
            print("❌ Timeout waiting for game to load")
            return False
        except Exception as e:
            print(f"❌ Error navigating to game: {e}")
            return False
    
    def extract_card(self, card_element) -> Optional[Dict]:
        """Extract card information from a card element"""
        try:
            # Try multiple methods to extract card data
            card_data = {}
            
            # Method 1: Data attributes
            rank = card_element.get_attribute('data-rank')
            suit = card_element.get_attribute('data-suit')
            
            # Method 2: Class names (Evolution often uses classes like 'card-10H' for 10 of Hearts)
            if not rank:
                classes = card_element.get_attribute('class')
                if classes:
                    # Parse class names for card info
                    for cls in classes.split():
                        if 'card-' in cls:
                            card_str = cls.replace('card-', '')
                            # Extract rank and suit from string like '10H' or 'AS'
                            if len(card_str) >= 2:
                                if card_str[0:2] == '10':
                                    rank = '10'
                                    suit = card_str[2] if len(card_str) > 2 else ''
                                else:
                                    rank = card_str[0]
                                    suit = card_str[1] if len(card_str) > 1 else ''
            
            # Method 3: Inner elements
            if not rank:
                try:
                    rank_elem = card_element.find_element(By.CSS_SELECTOR, self.selectors['card_rank'])
                    rank = rank_elem.text or rank_elem.get_attribute('data-value')
                except:
                    pass
            
            if not suit:
                try:
                    suit_elem = card_element.find_element(By.CSS_SELECTOR, self.selectors['card_suit'])
                    suit = suit_elem.get_attribute('class').split()[-1]  # Often the suit is a class
                except:
                    pass
            
            # Method 4: Image analysis (card might be displayed as background image)
            if not rank:
                style = card_element.get_attribute('style')
                if style and 'background' in style:
                    # Parse background image URL for card info
                    # URLs often contain card names like 'KH.png' for King of Hearts
                    import re
                    match = re.search(r'/([AKQJ2-9]|10)([HDCS])\.(png|jpg|svg)', style)
                    if match:
                        rank = match.group(1)
                        suit = match.group(2)
            
            if rank:
                # Normalize suit names
                suit_map = {'H': 'hearts', 'D': 'diamonds', 'C': 'clubs', 'S': 'spades'}
                if suit in suit_map:
                    suit = suit_map[suit]
                
                return {'rank': rank, 'suit': suit}
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error extracting card: {e}")
            return None
    
    def get_game_state(self) -> Optional[GameState]:
        """Extract current game state from the DOM"""
        try:
            # Extract player cards
            player_cards = []
            try:
                # Try primary selector
                card_elements = self.driver.find_elements(By.CSS_SELECTOR, self.selectors['player_cards'])
                if not card_elements:
                    # Try alternative selector
                    card_elements = self.driver.find_elements(By.CSS_SELECTOR, self.selectors['alt_player_cards'])
                
                for elem in card_elements:
                    card = self.extract_card(elem)
                    if card:
                        player_cards.append(card)
            except:
                pass
            
            # Extract dealer cards
            dealer_cards = []
            try:
                card_elements = self.driver.find_elements(By.CSS_SELECTOR, self.selectors['dealer_cards'])
                if not card_elements:
                    card_elements = self.driver.find_elements(By.CSS_SELECTOR, self.selectors['alt_dealer_cards'])
                
                for elem in card_elements:
                    card = self.extract_card(elem)
                    if card:
                        dealer_cards.append(card)
            except:
                pass
            
            # Get scores directly from display if available
            player_total = 0
            dealer_total = 0
            
            try:
                score_elem = self.driver.find_element(By.CSS_SELECTOR, self.selectors['player_score'])
                player_total = int(score_elem.text)
            except:
                # Calculate from cards
                player_total = self.calculate_hand_total(player_cards)
            
            try:
                score_elem = self.driver.find_element(By.CSS_SELECTOR, self.selectors['dealer_score'])
                dealer_total = int(score_elem.text)
            except:
                # Calculate from visible dealer cards
                dealer_total = self.calculate_hand_total(dealer_cards)
            
            # Check available actions
            can_hit = self.is_button_enabled(self.selectors['hit_button'])
            can_stand = self.is_button_enabled(self.selectors['stand_button'])
            can_double = self.is_button_enabled(self.selectors['double_button'])
            can_split = self.is_button_enabled(self.selectors['split_button'])
            
            # Get balance and bet
            balance = self.get_text_as_float(self.selectors['balance'])
            bet_amount = self.get_text_as_float(self.selectors['total_bet'])
            
            # Get game status
            game_status = self.get_text(self.selectors['game_phase']) or "unknown"
            
            # Check if hand is soft
            is_soft = self.is_hand_soft(player_cards)
            
            return GameState(
                player_cards=player_cards,
                dealer_cards=dealer_cards,
                player_total=player_total,
                dealer_total=dealer_total,
                is_soft=is_soft,
                can_hit=can_hit,
                can_stand=can_stand,
                can_double=can_double,
                can_split=can_split,
                balance=balance,
                bet_amount=bet_amount,
                game_status=game_status,
                timestamp=int(time.time() * 1000)
            )
            
        except Exception as e:
            print(f"⚠️ Error getting game state: {e}")
            return None
    
    def calculate_hand_total(self, cards: List[Dict]) -> int:
        """Calculate blackjack hand total"""
        total = 0
        aces = 0
        
        for card in cards:
            rank = card.get('rank', '')
            if rank == 'A':
                aces += 1
                total += 11
            elif rank in ['K', 'Q', 'J']:
                total += 10
            else:
                try:
                    total += int(rank)
                except:
                    pass
        
        # Adjust for aces
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        
        return total
    
    def is_hand_soft(self, cards: List[Dict]) -> bool:
        """Check if hand is soft (has ace counted as 11)"""
        total = 0
        has_ace = False
        
        for card in cards:
            rank = card.get('rank', '')
            if rank == 'A':
                has_ace = True
                total += 11
            elif rank in ['K', 'Q', 'J']:
                total += 10
            else:
                try:
                    total += int(rank)
                except:
                    pass
        
        return has_ace and total <= 21
    
    def is_button_enabled(self, selector: str) -> bool:
        """Check if an action button is enabled"""
        try:
            button = self.driver.find_element(By.CSS_SELECTOR, selector)
            return button.is_enabled() and button.is_displayed()
        except:
            return False
    
    def get_text(self, selector: str) -> Optional[str]:
        """Get text from an element"""
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            return elem.text
        except:
            return None
    
    def get_text_as_float(self, selector: str) -> float:
        """Get text as float value"""
        try:
            text = self.get_text(selector)
            if text:
                # Remove currency symbols and commas
                cleaned = ''.join(c for c in text if c.isdigit() or c == '.')
                return float(cleaned)
        except:
            pass
        return 0.0
    
    def click_action(self, action: Action) -> bool:
        """Click an action button"""
        try:
            selector_map = {
                Action.HIT: self.selectors['hit_button'],
                Action.STAND: self.selectors['stand_button'],
                Action.DOUBLE: self.selectors['double_button'],
                Action.SPLIT: self.selectors['split_button']
            }
            
            selector = selector_map.get(action)
            if selector:
                button = self.driver.find_element(By.CSS_SELECTOR, selector)
                if button.is_enabled():
                    button.click()
                    print(f"✅ Clicked {action.value}")
                    return True
                else:
                    print(f"⚠️ Button {action.value} is disabled")
            
        except Exception as e:
            print(f"❌ Error clicking {action.value}: {e}")
        
        return False
    
    def monitor_and_play(self, auto_play: bool = False):
        """Monitor the game and optionally auto-play with optimal strategy"""
        print("🎮 Starting game monitoring...")
        print(f"Auto-play: {'Enabled' if auto_play else 'Disabled (recommendations only)'}")
        
        last_state = None
        
        while True:
            try:
                # Get current game state
                state = self.get_game_state()
                
                if state and state != last_state:
                    # State changed, analyze it
                    print(f"\n📊 Game State Update:")
                    print(f"  Player: {state.player_total} {'(soft)' if state.is_soft else ''}")
                    print(f"  Dealer: {state.dealer_total}")
                    print(f"  Status: {state.game_status}")
                    
                    # Get strategy recommendation
                    if state.can_hit or state.can_stand or state.can_double or state.can_split:
                        game_dict = asdict(state)
                        game_dict['playerCards'] = state.player_cards
                        game_dict['dealerCards'] = state.dealer_cards
                        game_dict['playerTotal'] = state.player_total
                        game_dict['playerSoft'] = state.is_soft
                        game_dict['actions'] = {
                            'canHit': state.can_hit,
                            'canStand': state.can_stand,
                            'canDouble': state.can_double,
                            'canSplit': state.can_split
                        }
                        
                        recommendation = self.strategy_engine.analyze_game_state(game_dict)
                        
                        print(f"\n🎯 Strategy Recommendation:")
                        print(f"  Action: {recommendation.action.value.upper()}")
                        print(f"  Confidence: {recommendation.confidence:.0%}")
                        print(f"  Reasoning: {recommendation.reasoning}")
                        print(f"  Count: {recommendation.count_adjustment}")
                        
                        # Auto-play if enabled
                        if auto_play and recommendation.confidence >= 0.8:
                            time.sleep(1)  # Small delay to seem human
                            self.click_action(recommendation.action)
                    
                    # Get bet recommendation
                    if state.balance > 0:
                        bet_rec = self.strategy_engine.get_bet_recommendation(
                            bankroll=state.balance,
                            min_bet=1.0,
                            max_bet=min(500.0, state.balance * 0.1)
                        )
                        print(f"\n💰 Bet Recommendation:")
                        print(f"  Amount: ${bet_rec['recommended_bet']:.2f}")
                        print(f"  Confidence: {bet_rec['confidence']}")
                        print(f"  Reason: {bet_rec['reason']}")
                    
                    # Store state
                    self.game_state_history.append(state)
                    last_state = state
                
                # Wait before next check
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print("\n👋 Stopping monitor...")
                break
            except Exception as e:
                print(f"⚠️ Monitor error: {e}")
                time.sleep(1)
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()

def main():
    """Main entry point"""
    print("🎰 Selenium Infinity Blackjack Assistant")
    print("=" * 50)
    
    # Get user preferences
    casino = input("Enter casino (draftkings/betmgm/fanduel) [draftkings]: ").strip() or "draftkings"
    auto_play = input("Enable auto-play? (y/n) [n]: ").strip().lower() == 'y'
    
    if auto_play:
        print("\n⚠️ WARNING: Auto-play is for educational purposes only!")
        print("Using this in real money games may violate casino terms of service.")
        confirm = input("Continue? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Exiting...")
            return
    
    # Create scraper
    scraper = SeleniumInfinityScraper(casino_site=casino, headless=False)
    
    try:
        # Navigate to game
        if scraper.navigate_to_game():
            # Start monitoring
            scraper.monitor_and_play(auto_play=auto_play)
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
