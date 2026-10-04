import unittest

import bot


def event(game_id, completed, our_score, opp_score, team_id="130"):
    return {
        "id": game_id,
        "date": "2026-10-03T23:30Z",
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
                         [("1", "Michigan", 31, "Rival", 10, "2026-10-03")])

    def test_compose_yes(self):
        self.assertIn("Yes!", bot.compose_tweet("Michigan", 31, "Rival", 10))

    def test_compose_yes_above_31(self):
        self.assertIn("Yes!", bot.compose_tweet("Michigan", 45, "Rival", 10))

    def test_compose_no(self):
        text = bot.compose_tweet("Michigan", 30, "Rival", 10)
        self.assertIn("No.", text)
        self.assertIn("Michigan 30, Rival 10", text)

    def test_compose_full_text(self):
        self.assertEqual(
            bot.compose_tweet("NC State", 31, "Louisville", 28),
            "Did NC State score 31 points?\n\nYes! ✅\n\nNC State 31, Louisville 28\n\n"
            "Is Dave Doeren still employed?\n\nYes 😞",
        )


if __name__ == "__main__":
    unittest.main()
