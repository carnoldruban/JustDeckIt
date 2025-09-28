# Old App Analysis - Existing Src Folder Content

## Project Structure Analysis
The src folder contains a comprehensive blackjack tracking system with the following components:

### Core Application Files
- **tracker_app.py** - Main GUI application using CustomTkinter with modern dark UI
- **tracker_app_v2.py** - Alternative version of the main tracker
- **database_manager.py** - SQLite database operations with comprehensive logging
- **logging_config.py** - Detailed logging system with rotation and performance monitoring

### Card Management System
- **cards.py** - Card definitions and utilities
- **shoe.py** - Individual shoe management
- **shoe_manager.py** - Multi-shoe coordination and state management
- **shuffling.py** - Shuffle algorithms (riffle, strip cut)

### Counting & Strategy
- **card_counter.py** - Hi-Lo and Wong Halves counting systems
- **strategy.py** - S17 basic strategy with deviations and bet recommendations
- **predictor.py** - Card prediction algorithms
- **prediction_validator.py** - Validation of prediction accuracy

### Data Collection
- **scraper.py** - Live Chrome WebSocket scraper for DraftKings/OLG
- **scraper_sim.py** - Simulation version for testing
- **page_reader.py** - Page content extraction
- **infinite_scraper_poc.py** - Proof of concept for continuous scraping

### Analytics & Monitoring
- **analytics_engine.py** - Performance analysis and recommendations
- **browser_activity_keeper.py** - Browser session management
- **inactivity_bypass.py** - Automatic page refresh to prevent timeouts
- **inactivity_handler.py** - Session timeout handling
- **refresh_game_page.py** - Page refresh utilities

### Utilities & Configuration
- **mcp_client.py** - MCP protocol client
- **mcp_settings_builder.py** - Settings configuration
- **simple_keeper.py** - Basic state keeper
- **debug_db.py** - Database debugging utilities

## Key Features Identified
1. **Multi-shoe tracking** with automatic switching
2. **Real-time card counting** (Hi-Lo, Wong Halves)
3. **Live web scraping** from casino sites
4. **Advanced shuffle tracking** with zone analysis
5. **Strategy recommendations** with true count deviations
6. **Comprehensive logging** and error handling
7. **Modern GUI** with dark theme and multiple tabs
8. **Database persistence** with SQLite
9. **Analytics engine** for performance tracking
10. **Inactivity handling** to maintain sessions

## Architecture Quality
- **Error Handling**: Comprehensive try-catch blocks throughout
- **Logging**: Detailed logging with rotation and performance metrics
- **Threading**: Proper thread management for UI and scraping
- **Database**: Robust SQLite implementation with proper locking
- **UI**: Modern CustomTkinter interface with responsive design
- **Modularity**: Well-separated concerns across multiple files