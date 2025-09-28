"""
Infinity Blackjack Scraper
Connects to Evolution Gaming iframe across different casino sites
Extracts game data using DOM selectors via Chrome DevTools Protocol
"""

import asyncio
import json
import websockets
import requests
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class GameState(Enum):
    WAITING = "waiting"
    BETTING = "betting"
    DEALING = "dealing"
    PLAYER_TURN = "player_turn"
    DEALER_TURN = "dealer_turn"
    FINISHED = "finished"

@dataclass
class Card:
    suit: str  # 'hearts', 'diamonds', 'clubs', 'spades'
    rank: str  # 'A', '2'-'10', 'J', 'Q', 'K'
    value: int  # Blackjack value

@dataclass
class Hand:
    cards: List[Card]
    total: int
    is_soft: bool
    is_blackjack: bool
    is_bust: bool

class InfinityBlackjackScraper:
    """
    Scraper for Infinity Blackjack tables using Chrome DevTools Protocol.
    Works with Evolution Gaming iframes across multiple casino sites.
    """
    
    def __init__(self, debug_port: int = 9222):
        self.debug_port = debug_port
        self.chrome_url = f"http://127.0.0.1:{debug_port}"
        self.websocket = None
        self.session_id = None
        self.iframe_session_id = None
        self.request_id = 1
        self.game_state = GameState.WAITING
        self.callbacks = {}
        
        # Evolution Gaming iframe identifier
        self.IFRAME_IDENTIFIER = "evo-games.com"
        
        # DOM Selectors for Infinity Blackjack
        # These need to be mapped based on actual Evolution Gaming interface
        self.selectors = {
            # Card selectors
            'player_cards': '.player-cards .card',
            'dealer_cards': '.dealer-cards .card',
            'common_cards': '.common-cards .card',  # Infinity uses common cards
            
            # Value displays
            'player_total': '.player-hand-value',
            'dealer_total': '.dealer-hand-value',
            
            # Action buttons
            'hit_button': 'button[data-action="hit"]',
            'stand_button': 'button[data-action="stand"]',
            'double_button': 'button[data-action="double"]',
            'split_button': 'button[data-action="split"]',
            'insurance_button': 'button[data-action="insurance"]',
            
            # Game state indicators
            'game_status': '.game-status',
            'bet_amount': '.bet-amount',
            'balance': '.balance-amount',
            'win_amount': '.win-amount',
            
            # Infinity specific
            'decision_timer': '.decision-timer',
            'players_count': '.players-online',
            'your_decision': '.your-decision-indicator'
        }
        
    async def connect(self) -> bool:
        """Connect to Chrome DevTools Protocol"""
        try:
            # Get available targets
            response = requests.get(f"{self.chrome_url}/json/list")
            response.raise_for_status()
            targets = response.json()
            
            # Find a tab with casino site
            casino_tab = None
            for target in targets:
                url = target.get('url', '')
                # Check for common casino sites
                if any(site in url for site in ['draftkings', 'betmgm', 'caesars', 'fanduel', 'olg']):
                    casino_tab = target
                    print(f"✅ Found casino tab: {target.get('title')}")
                    break
            
            if not casino_tab:
                print("❌ No casino tab found. Please open a casino site first.")
                return False
            
            # Connect to the WebSocket
            ws_url = casino_tab.get('webSocketDebuggerUrl')
            if not ws_url:
                print("❌ WebSocket URL not available. Chrome must be started with --remote-debugging-port")
                return False
            
            self.websocket = await websockets.connect(ws_url, max_size=10**8)
            print(f"✅ Connected to Chrome DevTools")
            
            # Find and attach to Evolution Gaming iframe
            await self._attach_to_iframe()
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def _attach_to_iframe(self):
        """Find and attach to Evolution Gaming iframe"""
        # Get all frames
        await self._send_command("Page.enable")
        await self._send_command("Runtime.enable")
        
        # Get frame tree
        result = await self._send_command("Page.getFrameTree")
        frame_tree = result.get('frameTree', {})
        
        # Find Evolution Gaming iframe
        iframe_found = False
        await self._find_evo_iframe(frame_tree)
        
        if self.iframe_session_id:
            print(f"✅ Attached to Evolution Gaming iframe")
            # Enable necessary domains in iframe context
            await self._send_command("Runtime.enable", session_id=self.iframe_session_id)
            await self._send_command("DOM.enable", session_id=self.iframe_session_id)
        else:
            print("⚠️ Evolution Gaming iframe not found. It may load later.")
    
    async def _find_evo_iframe(self, frame_tree: dict):
        """Recursively find Evolution Gaming iframe in frame tree"""
        frame = frame_tree.get('frame', {})
        url = frame.get('url', '')
        
        if self.IFRAME_IDENTIFIER in url:
            # Found the iframe, create isolated world
            frame_id = frame.get('id')
            result = await self._send_command("Target.attachToTarget", {
                "targetId": frame_id,
                "flatten": True
            })
            self.iframe_session_id = result.get('sessionId')
            return True
        
        # Check child frames
        for child in frame_tree.get('childFrames', []):
            if await self._find_evo_iframe(child):
                return True
        
        return False
    
    async def _send_command(self, method: str, params: dict = None, session_id: str = None) -> dict:
        """Send command to Chrome DevTools"""
        command = {
            "id": self.request_id,
            "method": method
        }
        
        if params:
            command["params"] = params
        
        if session_id:
            command["sessionId"] = session_id
        
        self.request_id += 1
        
        # Store callback for this request
        request_id = command["id"]
        future = asyncio.Future()
        self.callbacks[request_id] = future
        
        await self.websocket.send(json.dumps(command))
        
        # Wait for response
        return await future
    
    async def evaluate_script(self, script: str) -> Any:
        """Execute JavaScript in the iframe context"""
        result = await self._send_command(
            "Runtime.evaluate",
            {
                "expression": script,
                "returnByValue": True
            },
            session_id=self.iframe_session_id
        )
        
        if result.get('result', {}).get('value'):
            return result['result']['value']
        return None
    
    async def get_game_state(self) -> Dict:
        """Extract current game state from DOM"""
        # JavaScript to extract all game data
        extraction_script = '''
        (() => {
            const extractCard = (element) => {
                // Extract card data from element
                // This needs to be adapted based on actual DOM structure
                const classes = element.className;
                const rank = element.getAttribute('data-rank') || 
                           element.querySelector('.rank')?.textContent || '';
                const suit = element.getAttribute('data-suit') || 
                           element.querySelector('.suit')?.className || '';
                return { rank, suit };
            };
            
            const calculateTotal = (cards) => {
                let total = 0;
                let aces = 0;
                
                cards.forEach(card => {
                    if (card.rank === 'A') {
                        aces++;
                        total += 11;
                    } else if (['K', 'Q', 'J'].includes(card.rank)) {
                        total += 10;
                    } else {
                        total += parseInt(card.rank) || 0;
                    }
                });
                
                // Adjust for aces
                while (total > 21 && aces > 0) {
                    total -= 10;
                    aces--;
                }
                
                return { total, soft: aces > 0 && total <= 21 };
            };
            
            // Extract player cards
            const playerCards = Array.from(document.querySelectorAll('%s'))
                .map(extractCard)
                .filter(c => c.rank);
            
            // Extract dealer cards
            const dealerCards = Array.from(document.querySelectorAll('%s'))
                .map(extractCard)
                .filter(c => c.rank);
            
            // Extract common cards (Infinity specific)
            const commonCards = Array.from(document.querySelectorAll('%s'))
                .map(extractCard)
                .filter(c => c.rank);
            
            // Get other game info
            const balance = document.querySelector('%s')?.textContent || '0';
            const betAmount = document.querySelector('%s')?.textContent || '0';
            const gameStatus = document.querySelector('%s')?.textContent || '';
            
            // Check available actions
            const canHit = !document.querySelector('%s')?.disabled;
            const canStand = !document.querySelector('%s')?.disabled;
            const canDouble = !document.querySelector('%s')?.disabled;
            const canSplit = !document.querySelector('%s')?.disabled;
            
            // Calculate totals
            const playerTotal = calculateTotal(playerCards);
            const dealerTotal = calculateTotal(dealerCards);
            
            return {
                playerCards,
                dealerCards,
                commonCards,
                playerTotal: playerTotal.total,
                dealerTotal: dealerTotal.total,
                playerSoft: playerTotal.soft,
                dealerSoft: dealerTotal.soft,
                balance: parseFloat(balance.replace(/[^0-9.-]/g, '')) || 0,
                betAmount: parseFloat(betAmount.replace(/[^0-9.-]/g, '')) || 0,
                gameStatus,
                actions: {
                    canHit,
                    canStand,
                    canDouble,
                    canSplit
                },
                timestamp: Date.now()
            };
        })();
        ''' % (
            self.selectors['player_cards'],
            self.selectors['dealer_cards'],
            self.selectors['common_cards'],
            self.selectors['balance'],
            self.selectors['bet_amount'],
            self.selectors['game_status'],
            self.selectors['hit_button'],
            self.selectors['stand_button'],
            self.selectors['double_button'],
            self.selectors['split_button']
        )
        
        return await self.evaluate_script(extraction_script)
    
    async def monitor_game(self, callback=None):
        """Continuously monitor game state changes"""
        print("🎮 Starting game monitoring...")
        last_state = None
        
        while True:
            try:
                # Get current game state
                current_state = await self.get_game_state()
                
                # Check if state changed
                if current_state != last_state:
                    print(f"📊 Game state updated:")
                    print(f"  Player: {current_state.get('playerTotal')} "
                          f"{'(soft)' if current_state.get('playerSoft') else ''}")
                    print(f"  Dealer: {current_state.get('dealerTotal')}")
                    print(f"  Status: {current_state.get('gameStatus')}")
                    
                    # Call callback if provided
                    if callback:
                        await callback(current_state)
                    
                    last_state = current_state
                
                # Wait before next check
                await asyncio.sleep(0.5)  # Check twice per second
                
            except Exception as e:
                print(f"⚠️ Monitoring error: {e}")
                await asyncio.sleep(1)
    
    async def listen_for_messages(self):
        """Listen for Chrome DevTools messages"""
        while True:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                # Handle response to our commands
                if 'id' in data and data['id'] in self.callbacks:
                    future = self.callbacks.pop(data['id'])
                    if 'error' in data:
                        future.set_exception(Exception(data['error']))
                    else:
                        future.set_result(data.get('result', {}))
                
                # Handle events
                elif 'method' in data:
                    await self._handle_event(data)
                    
            except Exception as e:
                print(f"⚠️ Message handling error: {e}")
                break
    
    async def _handle_event(self, event: dict):
        """Handle Chrome DevTools events"""
        method = event.get('method')
        params = event.get('params', {})
        
        # Handle console messages from iframe
        if method == 'Runtime.consoleAPICalled' and event.get('sessionId') == self.iframe_session_id:
            args = params.get('args', [])
            if args:
                console_text = args[0].get('value', '')
                if 'blackjack' in console_text.lower() or 'infinity' in console_text.lower():
                    print(f"📝 Console: {console_text}")
    
    async def run(self):
        """Main run loop"""
        if not await self.connect():
            return
        
        # Start listening for messages
        listener_task = asyncio.create_task(self.listen_for_messages())
        
        # Start monitoring game
        monitor_task = asyncio.create_task(self.monitor_game())
        
        try:
            await asyncio.gather(listener_task, monitor_task)
        except KeyboardInterrupt:
            print("\n👋 Stopping scraper...")
        finally:
            if self.websocket:
                await self.websocket.close()

async def main():
    """Main entry point"""
    print("🎰 Infinity Blackjack Scraper")
    print("=" * 40)
    print("Make sure Chrome is running with:")
    print('chrome.exe --remote-debugging-port=9222')
    print("=" * 40)
    
    scraper = InfinityBlackjackScraper()
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())
