# 🎰 Infinity Blackjack Assistant

An advanced online blackjack assistant for Evolution Gaming's Infinity Blackjack tables. This tool provides real-time strategy recommendations, card counting, and game analysis across multiple casino platforms.

## ⚠️ Legal Disclaimer

**IMPORTANT: This software is for EDUCATIONAL PURPOSES ONLY.**

- Using automated tools or assistance software may violate the Terms of Service of online casinos
- This tool should NOT be used for real money gambling
- The authors are not responsible for any losses or account suspensions
- Always gamble responsibly and within your means

## 🎯 Features

### Core Capabilities
- **Cross-Casino Support**: Works with DraftKings, BetMGM, FanDuel, and other casinos using Evolution Gaming
- **Iframe Access**: Directly accesses Evolution Gaming iframe content across different casino sites
- **Real-time Analysis**: Monitors game state continuously and provides instant recommendations
- **Strategy Engine**: Implements perfect basic strategy for 6-8 deck games
- **Card Counting**: Multiple counting systems (Hi-Lo, Hi-Opt-I, Wong Halves)
- **Bet Sizing**: Kelly Criterion-based betting recommendations

### Advanced Features
- **Deviation Plays**: Adjusts strategy based on true count
- **Expected Value Calculations**: Shows EV difference between actions
- **Session Tracking**: Maintains complete hand history
- **Pattern Recognition**: Identifies trends and streaks
- **Auto-play Mode**: Can automatically execute optimal plays (educational only)

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- Google Chrome browser
- Windows/Mac/Linux operating system

### Setup Instructions

1. **Clone or Download the Repository**
```bash
cd injinityBJ_assistant
```

2. **Install Required Dependencies**
```bash
pip install -r requirements.txt
```

3. **Verify Chrome Installation**
- Ensure Google Chrome is installed on your system
- The tool will automatically download the appropriate ChromeDriver

## 📖 Usage Guide

### Method 1: Chrome DevTools Protocol (CDP)

This method connects to an existing Chrome instance with debugging enabled.

1. **Start Chrome with Debugging Port**
```bash
# Windows
chrome.exe --remote-debugging-port=9222

# Mac
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222
```

2. **Navigate to the Casino**
- Open your preferred casino site (DraftKings, BetMGM, etc.)
- Navigate to the Infinity Blackjack game
- Wait for the game to fully load

3. **Run the CDP Scraper**
```bash
python infinity_scraper.py
```

### Method 2: Selenium Automation (Recommended)

This method automatically launches and controls Chrome.

```bash
python selenium_infinity_scraper.py
```

When prompted:
- Enter casino name (draftkings/betmgm/fanduel)
- Choose whether to enable auto-play (educational mode only)

## 🎮 How It Works

### 1. Game State Extraction
The assistant monitors the DOM within the Evolution Gaming iframe to extract:
- Player and dealer cards
- Hand totals and soft/hard status
- Available actions (Hit, Stand, Double, Split)
- Balance and bet amounts
- Game phase and status

### 2. Strategy Analysis
For each game state, the strategy engine:
- Applies basic strategy rules
- Calculates true count from observed cards
- Checks for count-based deviations
- Computes expected value for each action
- Provides confidence-rated recommendations

### 3. Real-time Recommendations
The assistant displays:
```
🎯 Strategy Recommendation:
  Action: HIT
  Confidence: 95%
  Reasoning: Basic strategy recommendation
  Count: TC: 2.3 - Following basic strategy

💰 Bet Recommendation:
  Amount: $25.00
  Confidence: High
  Reason: True count: 2.3, Multiplier: 2x
```

## 🔧 Configuration

### Customizing Selectors

Edit the `selectors` dictionary in either scraper to match Evolution Gaming's current DOM structure:

```python
self.selectors = {
    'player_cards': 'div[data-role="player-cards"] div.card',
    'dealer_cards': 'div[data-role="dealer-cards"] div.card',
    # ... add or modify selectors as needed
}
```

### Strategy Settings

Modify strategy parameters in `strategy_engine.py`:

```python
# Initialize with custom rules
strategy = BasicStrategy(
    decks=8,                    # Number of decks
    dealer_stands_soft_17=True, # S17 or H17
    double_after_split=True,     # DAS allowed
    surrender_allowed=False      # Late surrender
)
```

### Card Counting System

Choose your preferred counting system:

```python
# Available systems: "hi-lo", "hi-opt-i", "wong-halves"
counter = CardCounter(system="hi-lo")
```

## 📊 Understanding the Output

### Game State Updates
```
📊 Game State Update:
  Player: 16 (soft)    # Your hand total
  Dealer: 10            # Dealer's up card
  Status: player_turn   # Current game phase
```

### Strategy Recommendations
- **Action**: The recommended play (Hit, Stand, Double, Split)
- **Confidence**: How certain the system is (based on count and EV)
- **Reasoning**: Why this action is recommended
- **Count Adjustment**: Current true count and any deviations

### Bet Recommendations
- **Amount**: Suggested bet size
- **Multiplier**: How many units to bet
- **True Count**: Current advantage/disadvantage
- **Kelly Fraction**: Optimal betting percentage

## 🛠️ Troubleshooting

### Common Issues

1. **"Chrome not found" Error**
   - Ensure Chrome is installed
   - Try specifying the full path to Chrome executable

2. **"Iframe not found" Error**
   - Wait for the game to fully load before running the scraper
   - Check that you're on the correct game page
   - Verify the casino site is supported

3. **"Selectors not working" Error**
   - Evolution Gaming may have updated their interface
   - Use browser DevTools to inspect and update selectors
   - Try the alternative selectors provided

4. **Connection Timeout**
   - Check your internet connection
   - Ensure the casino site isn't blocking automation
   - Try using a different casino platform

## 🔒 Security & Privacy

- **No Login Required**: The tool only reads game state, never accesses account info
- **Local Processing**: All analysis happens on your machine
- **No Data Collection**: No personal or game data is sent anywhere
- **Open Source**: Full code transparency

## 🚨 Responsible Gaming

Remember:
- The house always has an edge in blackjack
- Card counting requires significant practice and bankroll
- Online casinos may detect and ban advantage players
- Never gamble more than you can afford to lose
- If you have a gambling problem, seek help at www.begambleaware.org

## 📝 Technical Details

### Architecture
```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Casino Site    │────▶│ Evolution Gaming │────▶│   Game State   │
│  (DraftKings)   │     │     iframe       │     │   Extraction   │
└─────────────────┘     └──────────────────┘     └────────────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Recommendations│◀────│ Strategy Engine  │◀────│ Card Counter   │
│    Display      │     │ (Basic + Deviations)   │ (Hi-Lo System) │
└─────────────────┘     └──────────────────┘     └────────────────┘
```

### Technologies Used
- **Python 3.8+**: Core programming language
- **Selenium WebDriver**: Browser automation
- **Chrome DevTools Protocol**: Direct browser inspection
- **WebSockets**: Real-time communication
- **asyncio**: Asynchronous operations

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Evolution Gaming for creating Infinity Blackjack
- The blackjack strategy community for optimal play research
- Stanford Wong, Edward Thorp, and other blackjack pioneers

## 📧 Contact & Support

For questions, issues, or suggestions:
- Open an issue on GitHub
- Educational discussions only
- No support for real money gambling

---

**Remember: This tool is for educational purposes only. Always gamble responsibly.**
