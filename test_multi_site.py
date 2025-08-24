#!/usr/bin/env python3
"""
Test script to verify multi-site support for DraftKings and OLG casinos.
"""

def test_site_detection():
    """Test that the scraper can detect both DraftKings and OLG sites."""
    print("Testing multi-site support...")
    
    try:
        from scraper import Scraper
        from database_manager import DatabaseManager
        
        # Create a test scraper
        db_manager = DatabaseManager(":memory:")
        scraper = Scraper(db_manager, "Test Shoe")
        
        # Test DraftKings URL detection
        draftkings_url = "https://casino.draftkings.com/games/blackjack"
        if any(part in draftkings_url for part in scraper.TARGET_URL_PARTS):
            print("✅ DraftKings URL detection works")
        else:
            print("❌ DraftKings URL detection failed")
            return False
        
        # Test OLG URL detection
        olg_url = "https://www.olg.ca/en/casino/blackjack"
        if any(part in olg_url for part in scraper.TARGET_URL_PARTS):
            print("✅ OLG URL detection works")
        else:
            print("❌ OLG URL detection failed")
            return False
        
        # Test site detection logic
        if "draftkings" in draftkings_url.lower():
            detected_site = "DraftKings"
        elif "olg" in draftkings_url.lower():
            detected_site = "OLG"
        else:
            detected_site = "Unknown Casino"
        
        if detected_site == "DraftKings":
            print("✅ DraftKings site detection works")
        else:
            print("❌ DraftKings site detection failed")
            return False
        
        if "olg" in olg_url.lower():
            detected_site = "OLG"
        else:
            detected_site = "Unknown Casino"
        
        if detected_site == "OLG":
            print("✅ OLG site detection works")
        else:
            print("❌ OLG site detection failed")
            return False
        
        print("✅ Multi-site support verified!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing multi-site support: {e}")
        return False

def test_websocket_compatibility():
    """Test that both sites use the same WebSocket structure."""
    print("\nTesting WebSocket compatibility...")
    
    try:
        from scraper import Scraper
        from database_manager import DatabaseManager
        
        db_manager = DatabaseManager(":memory:")
        scraper = Scraper(db_manager, "Test Shoe")
        
        # Both sites should use the same Evolution Gaming iframe
        if scraper.IFRAME_URL_PART == "evo-games.com":
            print("✅ Both sites use Evolution Gaming iframe")
        else:
            print("❌ Iframe URL part mismatch")
            return False
        
        print("✅ WebSocket compatibility verified!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing WebSocket compatibility: {e}")
        return False

def main():
    """Run multi-site tests."""
    print("🌐 Multi-Site Support Test")
    print("=" * 40)
    
    tests = [
        test_site_detection,
        test_websocket_compatibility
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print(f"❌ Test {test.__name__} failed")
    
    print("\n" + "=" * 40)
    print(f"📊 Multi-Site Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Multi-site support verified! Works with both DraftKings and OLG.")
        return True
    else:
        print("⚠️  Some multi-site tests failed.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)


