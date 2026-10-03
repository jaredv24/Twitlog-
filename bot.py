"""Did my team score 31? A Twitter/X bot.

After each finished game, posts whether TEAM_ID scored at least 31 points.
Game results come from ESPN's public college football API; posts go out via
the X API v2. Already-posted games are recorded in posted.json so each game is
only tweeted once.
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/college-football"
STATE_FILE = Path(__file__).with_name("posted.json")
TARGET = 31


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "did-we-score-31-bot"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def parse_score(score):
    # The schedule endpoint returns {"value": 31.0, "displayValue": "31"};
    # the scoreboard endpoint returns a plain string.
    if isinstance(score, dict):
        score = score.get("value", score.get("displayValue"))
    return int(float(score))


def finished_games(schedule, team_id):
    """Yield (game_id, our_name, our_score, opp_name, opp_score) for completed games."""
    for event in schedule.get("events", []):
        comp = event["competitions"][0]
        if not comp["status"]["type"].get("completed"):
            continue
        teams = comp["competitors"]
        ours = next((c for c in teams if str(c["team"]["id"]) == str(team_id)), None)
        theirs = next((c for c in teams if c is not ours), None)
        if ours is None or theirs is None or "score" not in ours:
            continue
        yield (
            str(event["id"]),
            ours["team"].get("shortDisplayName") or ours["team"]["displayName"],
            parse_score(ours["score"]),
            theirs["team"].get("shortDisplayName") or theirs["team"]["displayName"],
            parse_score(theirs["score"]),
        )


def compose_tweet(team, score, opp, opp_score):
    if score >= TARGET:
        return f"Did {team} score 31 points?\n\nYES! 🎉\n\n{team} {score}, {opp} {opp_score}"
    return f"Did {team} score 31 points?\n\nNo.\n\n{team} {score}, {opp} {opp_score}"


def load_state():
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def save_state(posted):
    STATE_FILE.write_text(json.dumps(sorted(posted), indent=2) + "\n")


def post_tweet(text):
    import tweepy

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    client.create_tweet(text=text)


def run(team_id, dry_run=False, backfill=False):
    schedule = fetch_json(f"{ESPN_BASE}/teams/{team_id}/schedule")
    posted = load_state()
    new_games = [g for g in finished_games(schedule, team_id) if g[0] not in posted]

    if backfill:
        # Mark every game already played as handled without tweeting, so a
        # fresh install doesn't spam the whole season's results at once.
        posted.update(g[0] for g in new_games)
        save_state(posted)
        print(f"Marked {len(new_games)} past game(s) as posted.")
        return

    for game_id, team, score, opp, opp_score in new_games:
        text = compose_tweet(team, score, opp, opp_score)
        print(f"--- game {game_id} ---\n{text}")
        if not dry_run:
            post_tweet(text)
            posted.add(game_id)
            save_state(posted)
    if not new_games:
        print("No newly finished games.")


def search_teams(query):
    data = fetch_json(f"{ESPN_BASE}/teams?limit=1000")
    for entry in data["sports"][0]["leagues"][0]["teams"]:
        t = entry["team"]
        if query.lower() in t["displayName"].lower():
            print(f"{t['id']:>6}  {t['displayName']}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--team-id", default=os.environ.get("TEAM_ID"), help="ESPN team id")
    p.add_argument("--dry-run", action="store_true", help="print tweets instead of posting")
    p.add_argument("--backfill", action="store_true", help="mark past games as posted")
    p.add_argument("--search", metavar="NAME", help="look up a team's ESPN id")
    args = p.parse_args()

    if args.search:
        search_teams(args.search)
        return
    if not args.team_id:
        sys.exit("Set TEAM_ID (or pass --team-id). Find it with --search 'Team Name'.")
    run(args.team_id, dry_run=args.dry_run, backfill=args.backfill)


if __name__ == "__main__":
    main()
