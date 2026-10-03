import unittest

import bot


def event(game_id, completed, our_score, opp_score, team_id="130"):
    return {
        "id": game_id,
        "competitions": [{
            "status": {"type": {"completed": completed}},
            "competitors": [
                {"team": {"id": "999", "displayName": "Rival State", "shortDisplayName": "Rival"},
                 "score": {"value": float(opp_score), "displayValue": str(opp_score)}},
                {"team": {"id": team_id, "displayName": "Michigan Wolverines", "shortDisplayName": "Michigan"},
                 "score": str(our_score)},
            ],
        }],
    }


class BotTests(unittest.TestCase):
    def test_finished_games_skips_incomplete(self):
        schedule = {"events": [event("1", True, 31, 10), event("2", False, 0, 0)]}
        self.assertEqual(list(bot.finished_games(schedule, 130)),
                         [("1", "Michigan", 31, "Rival", 10)])

    def test_compose_yes(self):
        self.assertIn("YES", bot.compose_tweet("Michigan", 31, "Rival", 10))

    def test_compose_no(self):
        text = bot.compose_tweet("Michigan", 30, "Rival", 10)
        self.assertIn("No.", text)
        self.assertIn("Michigan 30, Rival 10", text)


if __name__ == "__main__":
    unittest.main()
