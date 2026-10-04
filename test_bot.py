import unittest
from datetime import datetime

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


    def test_game_window(self):
        # Saturday 7:30 PM ET kickoff (23:30 UTC).
        schedule = {"events": [event("1", False, 0, 0)]}
        at = lambda *a: datetime(*a, tzinfo=bot.ET)
        start, end = at(2026, 10, 3, 12), at(2026, 10, 4, 2)
        self.assertEqual(bot.game_window(schedule, set(), at(2026, 10, 3, 15)), (start, end))
        # Armed 12 hours before noon, so a late-starting GitHub run still waits for it.
        self.assertEqual(bot.game_window(schedule, set(), at(2026, 10, 3, 0)), (start, end))
        self.assertIsNone(bot.game_window(schedule, set(), at(2026, 10, 2, 23)))
        self.assertIsNone(bot.game_window(schedule, set(), at(2026, 10, 4, 2)))
        # Once tweeted, the bot stops watching.
        self.assertIsNone(bot.game_window(schedule, {"1"}, at(2026, 10, 3, 15)))

    def test_game_window_late_kickoff(self):
        # 10:30 PM ET kickoff runs past 2 AM, so the window stretches to kickoff + 5h.
        schedule = {"events": [dict(event("1", False, 0, 0), date="2026-10-04T02:30Z")]}
        _, end = bot.game_window(schedule, set(), datetime(2026, 10, 3, 23, tzinfo=bot.ET))
        self.assertEqual(end, datetime(2026, 10, 4, 3, 30, tzinfo=bot.ET))


if __name__ == "__main__":
    unittest.main()
