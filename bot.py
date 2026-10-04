"""Did my team score 31? A Twitter/X bot.

After each finished game, posts whether TEAM_ID scored at least 31 points.
Game results come from ESPN's public college football API; posts go out via
the X API v2. Already-posted games are recorded in posted.json so each game is
only tweeted once.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ESPN_HOSTS = ["https://site.api.espn.com", "https://site.web.api.espn.com"]
ESPN_PATH = "/apis/site/v2/sports/football/college-football"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json",
}
STATE_FILE = Path(__file__).with_name("posted.json")
SAVE_SCRIPT = Path(__file__).with_name("save_state.sh")
TARGET = 31

# Game-day watching: on a game day the bot stays running from noon ET until
# 2 AM ET the next night, checking every few minutes. A run that starts up to
# ARM_HOURS before noon waits for the window, since GitHub's schedule can
# start runs hours late.
ET = ZoneInfo("America/New_York")
WINDOW_START_HOUR = 12
WINDOW_END_HOUR = 2
ARM_HOURS = 12
POLL_SECONDS = 300
# GitHub stops a job after 6 hours, so hand off to a fresh run before then.
RUN_LIMIT = timedelta(hours=5, minutes=30)


def fetch_json(path):
    """GET an ESPN API path, trying each ESPN host until one answers."""
    error = None
    for host in ESPN_HOSTS:
        req = urllib.request.Request(host + ESPN_PATH + path, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            print(f"{req.full_url} -> HTTP {e.code}")
            error = e
    raise error


def parse_score(score):
    # The schedule endpoint returns {"value": 31.0, "displayValue": "31"};
    # the scoreboard endpoint returns a plain string.
    if isinstance(score, dict):
        score = score.get("value", score.get("displayValue"))
    return int(float(score))


def finished_games(schedule, team_id):
    """Yield (game_id, our_name, our_score, opp_name, opp_score, date) for completed games.

    date is the kickoff date in UTC, as YYYY-MM-DD.
    """
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
            event.get("date", "")[:10],
        )


def compose_tweet(team, score, opp, opp_score):
    answer = "Yes! ✅" if score >= TARGET else "No."
    return (
        f"Did {team} score 31 points?\n\n{answer}\n\n"
        f"{team} {score}, {opp} {opp_score}\n\n"
        "Is Dave Doeren still employed?\n\nYes 😞"
    )


def parse_kickoff(date):
    # ESPN dates look like "2026-10-03T23:30Z".
    return datetime.fromisoformat(date.replace("Z", "+00:00"))


def game_window(schedule, posted, now):
    """Return (start, end) of the game-day window the bot should be watching now, or None.

    A game's window runs from noon ET on its kickoff day until 2 AM ET the
    next day (later if kickoff is so late the game could run past that).
    It counts as active from ARM_HOURS before the start until the end, as
    long as the game hasn't been tweeted yet.
    """
    for event in schedule.get("events", []):
        if str(event["id"]) in posted or not event.get("date"):
            continue
        kickoff = parse_kickoff(event["date"])
        day = kickoff.astimezone(ET).date()
        start = datetime(day.year, day.month, day.day, WINDOW_START_HOUR, tzinfo=ET)
        next_day = day + timedelta(days=1)
        end = datetime(next_day.year, next_day.month, next_day.day, WINDOW_END_HOUR, tzinfo=ET)
        end = max(end, kickoff + timedelta(hours=5))
        if start - timedelta(hours=ARM_HOURS) <= now < end:
            return start, end
    return None


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


def run(team_id, dry_run=False, backfill=False, skip_before=None):
    schedule = fetch_json(f"/teams/{team_id}/schedule")
    posted = load_state()
    new_games = [g for g in finished_games(schedule, team_id) if g[0] not in posted]

    if backfill or skip_before:
        # Mark already-played games as handled without tweeting, so a fresh
        # install doesn't spam the whole season's results at once. With
        # skip_before, only games before that date are skipped.
        skipped = [g for g in new_games if backfill or g[5] < skip_before]
        for g in skipped:
            print(f"Skipping game {g[0]} ({g[5]}): {g[1]} {g[2]}, {g[3]} {g[4]}")
            posted.add(g[0])
        if not dry_run:
            save_state(posted)
        new_games = [g for g in new_games if g not in skipped]
        if backfill:
            return schedule

    for game_id, team, score, opp, opp_score, _ in new_games:
        text = compose_tweet(team, score, opp, opp_score)
        print(f"--- game {game_id} ---\n{text}")
        if not dry_run:
            post_tweet(text)
            posted.add(game_id)
            save_state(posted)
            if os.environ.get("GITHUB_ACTIONS"):
                # Commit the record right away, so nothing can tweet this
                # game again even if this run is cut off later.
                subprocess.run(["bash", str(SAVE_SCRIPT)], check=True)
    if not new_games:
        print("No newly finished games.")
    return schedule


def watch(team_id):
    """Keep checking through today's game-day window.

    Returns True if the window is still open when this run must stop, so
    the caller should hand off to a fresh run.
    """
    started = datetime.now(ET)
    while True:
        schedule = run(team_id)
        now = datetime.now(ET)
        window = game_window(schedule, load_state(), now)
        if window is None:
            print("Not in a game-day window; done.")
            return False
        start, end = window
        if now - started >= RUN_LIMIT:
            print(f"Game-day window open until {end:%a %I:%M %p %Z}; handing off.")
            return True
        print(f"Watching game day ({start:%a %I:%M %p} to {end:%a %I:%M %p %Z}); "
              f"next check in {POLL_SECONDS // 60} min.")
        time.sleep(POLL_SECONDS)


def search_teams(query):
    data = fetch_json("/teams?limit=1000")
    for entry in data["sports"][0]["leagues"][0]["teams"]:
        t = entry["team"]
        if query.lower() in t["displayName"].lower():
            print(f"{t['id']:>6}  {t['displayName']}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--team-id", default=os.environ.get("TEAM_ID"), help="ESPN team id")
    p.add_argument("--dry-run", action="store_true", help="print tweets instead of posting")
    p.add_argument("--backfill", action="store_true", help="mark past games as posted")
    p.add_argument("--skip-before", metavar="YYYY-MM-DD",
                   help="mark games before this date as posted, then post the rest")
    p.add_argument("--watch", action="store_true",
                   help="on game days, keep checking from noon to 2 AM ET")
    p.add_argument("--search", metavar="NAME", help="look up a team's ESPN id")
    args = p.parse_args()

    if args.search:
        search_teams(args.search)
        return
    if not args.team_id:
        sys.exit("Set TEAM_ID (or pass --team-id). Find it with --search 'Team Name'.")
    if args.watch:
        if watch(args.team_id) and os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write("continue=true\n")
        return
    run(args.team_id, dry_run=args.dry_run, backfill=args.backfill,
        skip_before=args.skip_before)


if __name__ == "__main__":
    main()
