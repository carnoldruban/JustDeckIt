"""
Complete Demo Startup Script - Sets up 2-hour tracking history and launches the app
"""

import subprocess
import sys
import time
import os
from datetime import datetime

def print_banner():
    print("=" * 70)
    print("🎰 ENHANCED BLACKJACK TRACKER - DEMO ENVIRONMENT")
    print("=" * 70)
    print("This script will:")
    print("1. Set up 2 hours of realistic tracking data")
    print("2. Launch the tracker app with all enhanced features")
    print("3. Optionally run live card simulation")
    print("=" * 70)

def run_setup():
    """Run the demo environment setup."""
    print("\n🚀 STEP 1: Setting up demo environment...")
    print("This will create 2 hours of realistic tracking data")
    
    try:
        result = subprocess.run([sys.executable, "setup_demo_environment.py"], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Demo environment setup completed!")
            print(result.stdout[-500:])  # Show last 500 chars of output
            return True
        else:
            print(f"❌ Setup failed: {result.stderr}")
            return False
    
    except subprocess.TimeoutExpired:
        print("⏰ Setup taking longer than expected, but continuing...")
        return True
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return False

def launch_tracker_app():
    """Launch the tracker app."""
    print("\n🚀 STEP 2: Launching Enhanced Tracker App...")
    print("The app will open with:")
    print("  • 2 hours of historical tracking data")
    print("  • Analytics & Predictions tab with insights")
    print("  • Real-time recommendation engine")
    
    try:
        # Launch the app in background
        process = subprocess.Popen([sys.executable, "tracker_app.py"])
        print("✅ Tracker app launched!")
        print("💡 Go to the 'Analytics & Predictions' tab to see the enhanced features")
        return process
    except Exception as e:
        print(f"❌ Failed to launch app: {e}")
        return None

def offer_live_demo():
    """Offer to run the live demo."""
    print("\n🎮 STEP 3: Live Demo (Optional)")
    print("Would you like to run a live card simulation?")
    print("This will simulate cards being dealt in real-time while the app is running.")
    
    choice = input("Run live demo? (y/n): ").strip().lower()
    
    if choice in ['y', 'yes']:
        print("\n🎲 Starting live demo in 5 seconds...")
        print("💡 Watch the Analytics tab for real-time updates!")
        time.sleep(5)
        
        try:
            # Run live demo
            subprocess.Popen([sys.executable, "live_demo_feeder.py"])
            print("✅ Live demo started!")
            print("🔄 Cards are now being dealt automatically")
            return True
        except Exception as e:
            print(f"❌ Live demo failed: {e}")
            return False
    else:
        print("📋 No live demo - app is ready with historical data")
        return False

def show_demo_guide():
    """Show the user how to use the demo."""
    print("\n" + "=" * 70)
    print("🎯 HOW TO TEST THE ENHANCED FEATURES")
    print("=" * 70)
    
    print("\n📊 ANALYTICS & PREDICTIONS TAB:")
    print("  • Shoe Performance: See which shoes have higher win rates")
    print("  • Seat Performance: Identify seats with better outcomes")
    print("  • Decision Recommendations: Get play/don't play advice")
    print("  • Prediction Accuracy: Monitor shuffle prediction performance")
    
    print("\n🎰 KEY BENEFITS TO OBSERVE:")
    print("  • 'Should Play' recommendations based on patterns")
    print("  • Best shoe and seat identification")
    print("  • Real-time confidence levels")
    print("  • Historical performance trends")
    
    print("\n🔍 WHAT TO LOOK FOR:")
    print("  • Win rates above 50% indicate profitable opportunities")
    print("  • Confidence levels help you decide when to act")
    print("  • Seat performance shows optimal positioning")
    print("  • Prediction accuracy validates the system's reliability")
    
    print("\n💡 DEMO SCENARIO:")
    print("  • The app shows 2 hours of tracking as if you've been monitoring")
    print("  • Analytics reveal which conditions are most profitable")
    print("  • Recommendations guide your next moves")
    print("  • Live demo (if running) shows real-time feature updates")
    
    print("\n" + "=" * 70)

def main():
    """Main demo startup function."""
    print_banner()
    
    # Step 1: Setup demo environment
    if not run_setup():
        print("❌ Cannot continue without demo environment")
        return
    
    time.sleep(2)
    
    # Step 2: Launch tracker app
    app_process = launch_tracker_app()
    if not app_process:
        print("❌ Cannot launch tracker app")
        return
    
    time.sleep(3)
    
    # Step 3: Offer live demo
    live_demo_running = offer_live_demo()
    
    time.sleep(2)
    
    # Show demo guide
    show_demo_guide()
    
    # Keep script running
    print("\n🏃 DEMO IS NOW RUNNING!")
    print("Press Ctrl+C to stop all demo processes")
    
    try:
        # Wait for app to close or user interrupt
        app_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping demo...")
        try:
            app_process.terminate()
        except:
            pass
    
    print("🏁 Demo completed!")

if __name__ == "__main__":
    main()
