import unittest
import sys
import os

# Ensure the strategy module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from strategy import get_hand_value, get_strategy_action, get_bet_recommendation

class TestStrategyModule(unittest.TestCase):

    def test_get_hand_value(self):
        print("\n--- Testing Hand Value Calculations ---")
        # Hard totals
        self.assertEqual(get_hand_value(['K', '7']), (17, False))
        self.assertEqual(get_hand_value(['10', '6', 'Q']), (26, False))
        # Soft totals
        self.assertEqual(get_hand_value(['A', '7']), (18, True))
        self.assertEqual(get_hand_value(['A', '9']), (20, True))
        self.assertEqual(get_hand_value(['A', 'A', '6']), (18, True))
        self.assertEqual(get_hand_value(['A', '5', 'A']), (17, True))
        # Edge cases
        self.assertEqual(get_hand_value(['A', 'K']), (21, True))
        self.assertEqual(get_hand_value(['A', '10', 'A']), (12, False))
        print("✓ Hand value calculations are correct.")

    def test_bet_recommendation_ramp(self):
        print("\n--- Testing Bet Recommendation Ramp ---")
        self.assertEqual(get_bet_recommendation(0), 1)
        self.assertEqual(get_bet_recommendation(1), 1)
        self.assertEqual(get_bet_recommendation(1.5), 2)
        self.assertEqual(get_bet_recommendation(2), 2)
        self.assertEqual(get_bet_recommendation(3), 4)
        self.assertEqual(get_bet_recommendation(4), 6)
        self.assertEqual(get_bet_recommendation(5), 8)
        self.assertEqual(get_bet_recommendation(10), 8)
        print("✓ Bet recommendation ramp is correct.")

    def test_basic_strategy_actions(self):
        print("\n--- Testing Basic Strategy Actions (TC=0) ---")
        # Hard totals
        self.assertEqual(get_strategy_action(['10', '6'], '7'), 'H', "16 vs 7 should be Hit")
        self.assertEqual(get_strategy_action(['10', '2'], '6'), 'S', "12 vs 6 should be Stand")
        self.assertEqual(get_strategy_action(['7', '4'], '9'), 'D', "11 vs 9 should be Double")
        # Soft totals
        self.assertEqual(get_strategy_action(['A', '7'], '3'), 'D', "Soft 18 vs 3 should be Double")
        self.assertEqual(get_strategy_action(['A', '8'], '6'), 'D', "Soft 19 vs 6 should be Double in H17")
        self.assertEqual(get_strategy_action(['A', '6'], '7'), 'H', "Soft 17 vs 7 should be Hit")
        # Pairs
        self.assertEqual(get_strategy_action(['8', '8'], 'A'), 'P', "8,8 vs A should be Split")
        self.assertEqual(get_strategy_action(['9', '9'], '7'), 'S', "9,9 vs 7 should be Stand")
        self.assertEqual(get_strategy_action(['5', '5'], '8'), 'D', "5,5 vs 8 should be Double (as Hard 10)")
        print("✓ Basic strategy actions are correct.")

    def test_deviation_actions(self):
        print("\n--- Testing Hi-Lo Deviation Actions ---")
        # 16 vs 10: Stand at TC >= 0
        self.assertEqual(get_strategy_action(['10', '6'], '10', true_count=-1), 'H', "16 vs 10 (TC -1) should be Hit")
        self.assertEqual(get_strategy_action(['10', '6'], '10', true_count=0), 'S', "16 vs 10 (TC 0) should be Stand")
        self.assertEqual(get_strategy_action(['10', '6'], '10', true_count=2), 'S', "16 vs 10 (TC 2) should be Stand")

        # Insurance: Take at TC >= 3
        self.assertEqual(get_strategy_action(['K', 'Q'], 'A', true_count=2.9), 'S', "Insurance (TC < 3) should not be offered")
        self.assertEqual(get_strategy_action(['K', 'Q'], 'A', true_count=3), 'Insurance', "Insurance (TC >= 3) should be offered")

        # 10,10 vs 6: Split at TC >= 4
        self.assertEqual(get_strategy_action(['10', '10'], '6', true_count=3), 'S', "10,10 vs 6 (TC 3) should be Stand")
        self.assertEqual(get_strategy_action(['10', '10'], '6', true_count=4), 'P', "10,10 vs 6 (TC 4) should be Split")
        print("✓ Deviation actions are correct.")

if __name__ == '__main__':
    unittest.main()
