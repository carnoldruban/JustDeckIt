"""
Demo script to showcase the enhanced blackjack tracker features
Run this to see the new Analytics tab and enhanced predictions
"""

import tkinter as tk
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_enhanced_tracker():
    """Runs the enhanced blackjack tracker with all new features."""
    try:
        from tracker_app import BlackjackTrackerApp
        
        print("🚀 Starting Enhanced Blackjack Tracker...")
        print("\n✨ NEW FEATURES INCLUDED:")
        print("   📊 Analytics & Predictions Tab")
        print("   🎯 Real-time Card Range Predictions (Low/Mid/High)")
        print("   📈 Prediction Accuracy Tracking")
        print("   🏆 Performance Analysis & Recommendations")
        print("   🔄 Advanced Shuffle Validation")
        print("   🎮 Enhanced Inactivity Popup Handling")
        print("   💾 Comprehensive Database Analytics")
        print("   📋 Exportable Analysis Reports")
        print("\n🎮 Starting GUI...")
        
        root = tk.Tk()
        app = BlackjackTrackerApp(root)
        
        # Show welcome message in the app
        welcome_msg = """
=== ENHANCED BLACKJACK TRACKER FEATURES ===

🆕 NEW ANALYTICS TAB: 
   - Performance summaries for shoes and seats
   - Decision recommendations based on historical data
   - Exportable analysis reports

🎯 ENHANCED PREDICTIONS:
   - Next 5 card range predictions (Low/Mid/High)
   - Color-coded prediction display
   - Real-time prediction accuracy tracking

🔬 ADVANCED VALIDATION:
   - Compare shuffle predictions vs actual cards
   - Learn patterns to improve future predictions
   - Track prediction errors and offsets

📊 COMPREHENSIVE ANALYTICS:
   - Seat performance statistics
   - Shoe win/loss analysis
   - Hourly performance trends
   - Decision support recommendations

🤖 IMPROVED AUTOMATION:
   - Enhanced inactivity popup detection
   - Multiple selector patterns for reliability
   - Automatic session tracking

Ready for hours of continuous monitoring and analysis!
        """
        
        app.update_game_display(welcome_msg + "\n")
        
        print("✅ Enhanced Blackjack Tracker is running!")
        print("   Check out the new 'Analytics & Predictions' tab!")
        
        root.mainloop()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all required packages are installed:")
        print("   pip install requests websockets")
    except Exception as e:
        print(f"❌ Error starting tracker: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_enhanced_tracker()
