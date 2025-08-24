#!/usr/bin/env python3
"""
Master script to run the entire comprehensive test suite for the Blackjack Tracker system.
This script will:
1. Generate 1000 rounds of test data
2. Run comprehensive tests with detailed logging
3. Monitor performance and memory usage
4. Generate detailed reports
"""

import os
import sys
import time
from datetime import datetime
from logging_config import get_logger, log_memory_usage

def main():
    """Run the complete comprehensive test suite."""
    logger = get_logger("MasterTest")
    
    print("🧪 COMPREHENSIVE BLACKJACK TRACKER TEST SUITE")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Log initial memory usage
    initial_memory = log_memory_usage("MasterTest")
    logger.info("Initial memory usage: %.2f MB", initial_memory)
    
    try:
        # Step 1: Generate test data
        print("📊 Step 1: Generating 1000 rounds of test data...")
        logger.info("Starting test data generation")
        
        from test_data_generator import TestDataGenerator
        generator = TestDataGenerator()
        
        start_time = time.time()
        rounds = generator.generate_1000_rounds()
        generation_time = time.time() - start_time
        
        print(f"✅ Generated {len(rounds)} rounds in {generation_time:.2f} seconds")
        logger.info("Test data generation completed in %.2f seconds", generation_time)
        
        # Save test data
        generator.save_rounds_to_file(rounds)
        stats = generator.get_statistics()
        print(f"📈 Statistics: {stats['total_shoes']} shoes, {stats['cards_dealt']} cards")
        
        # Step 2: Run comprehensive tests
        print("\n🔍 Step 2: Running comprehensive system tests...")
        logger.info("Starting comprehensive system tests")
        
        from comprehensive_test_runner import ComprehensiveTestRunner
        runner = ComprehensiveTestRunner()
        
        # Load test data
        if not runner.load_test_data():
            print("❌ Error: Could not load test data")
            return False
        
        # Run tests
        start_time = time.time()
        results = runner.run_comprehensive_test()
        test_time = time.time() - start_time
        
        print(f"✅ Tests completed in {test_time:.2f} seconds")
        logger.info("Comprehensive tests completed in %.2f seconds", test_time)
        
        # Step 3: Generate reports
        print("\n📋 Step 3: Generating detailed reports...")
        logger.info("Generating test reports")
        
        report = runner.generate_test_report()
        
        # Step 4: Display results
        print("\n📊 FINAL TEST RESULTS")
        print("=" * 40)
        print(f"Rounds Processed: {results['rounds_processed']}/{len(rounds)}")
        print(f"Success Rate: {results['performance_metrics']['success_rate']:.2f}%")
        print(f"Performance: {results['performance_metrics']['rounds_per_second']:.2f} rounds/sec")
        print(f"Total Time: {results['performance_metrics']['total_time_seconds']:.2f} seconds")
        print(f"Shoes Used: {results['shoes_used']}")
        print(f"Shuffles Performed: {results['shuffles_performed']}")
        print(f"Cards Processed: {results['cards_processed']}")
        print(f"Final Memory: {results['performance_metrics']['final_memory_mb']:.2f} MB")
        print(f"Errors: {len(results['errors'])}")
        
        # Step 5: Run basic system tests
        print("\n🔧 Step 4: Running basic system tests...")
        logger.info("Running basic system tests")
        
        from test_system import main as run_basic_tests
        basic_test_success = run_basic_tests()
        
        if basic_test_success:
            print("✅ Basic system tests passed")
        else:
            print("❌ Basic system tests failed")
        
        # Step 6: Run multi-site tests
        print("\n🌐 Step 5: Running multi-site compatibility tests...")
        logger.info("Running multi-site tests")
        
        from test_multi_site import main as run_multi_site_tests
        multi_site_success = run_multi_site_tests()
        
        if multi_site_success:
            print("✅ Multi-site compatibility tests passed")
        else:
            print("❌ Multi-site compatibility tests failed")
        
        # Final summary
        print("\n🎯 TEST SUITE SUMMARY")
        print("=" * 40)
        
        total_tests = 3  # comprehensive, basic, multi-site
        passed_tests = 0
        
        if results['performance_metrics']['success_rate'] > 95:
            passed_tests += 1
            print("✅ Comprehensive Test: PASSED")
        else:
            print("❌ Comprehensive Test: FAILED")
        
        if basic_test_success:
            passed_tests += 1
            print("✅ Basic System Test: PASSED")
        else:
            print("❌ Basic System Test: FAILED")
        
        if multi_site_success:
            passed_tests += 1
            print("✅ Multi-Site Test: PASSED")
        else:
            print("❌ Multi-Site Test: FAILED")
        
        print(f"\n📈 Overall Result: {passed_tests}/{total_tests} test suites passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! System is ready for production use.")
            logger.info("All test suites passed successfully")
            return True
        else:
            print("⚠️  Some tests failed. Please review the logs for details.")
            logger.warning("Some test suites failed")
            return False
        
    except Exception as e:
        print(f"❌ Critical error during testing: {e}")
        logger.error("Critical error during testing: %s", e)
        return False
    
    finally:
        # Final memory usage
        final_memory = log_memory_usage("MasterTest")
        memory_diff = final_memory - initial_memory
        print(f"\n💾 Memory Usage: {initial_memory:.2f} MB → {final_memory:.2f} MB (Δ{memory_diff:+.2f} MB)")
        logger.info("Final memory usage: %.2f MB (change: %+.2f MB)", final_memory, memory_diff)
        
        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def run_gui_test():
    """Run the GUI-based test interface."""
    print("🖥️  Starting GUI-based test interface...")
    
    from comprehensive_test_runner import ComprehensiveTestRunner
    runner = ComprehensiveTestRunner()
    
    # Load test data
    if not runner.load_test_data():
        print("❌ Error: Could not load test data. Run test_data_generator.py first.")
        return
    
    # Run GUI test
    runner.run_gui_test()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        run_gui_test()
    else:
        success = main()
        sys.exit(0 if success else 1)



