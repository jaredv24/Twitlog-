# Did we score 31?

A Twitter/X bot that, after every game, asks whether your college football team scored 31 points, and answers it. The answer is yes if they scored 31 or more:

```
Did NC State score 31 points?

Yes! ✅

NC State 34, UNC 20

Is Dave Doeren still employed?

Yes 😞
```

It runs for free on GitHub Actions. Every 30 minutes from Thursday to Sunday, it checks ESPN's public scoreboard. When a game has finished, it posts once. The IDs of games it has already posted are saved in `posted.json`.

## Setup

1. **Team.** It's set up for NC State (ESPN ID `152`). To use another team, set a `TEAM_ID` variable (step 3). Find a team's ID with `python bot.py --search "Team Name"`, or take the number from its ESPN URL, for example `espn.com/college-football/team/_/id/152/...`.

2. **Get X API keys.** Create an app at https://developer.x.com and set its permissions to **Read and write**. Then generate an API key and secret, plus an access token and secret, for the bot account.

3. **Configure the repo.** In GitHub, go to Settings → Secrets and variables → Actions:
   - Variables (optional): `TEAM_ID` to use a team other than NC State
   - Secrets: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`

4. **Skip games that were already played** so the bot doesn't post the whole season at once. Go to Actions → "Did we score 31?" → Run workflow, check **backfill**, then run it.

## Local testing

```
pip install -r requirements.txt
TEAM_ID=152 python bot.py --dry-run   # prints tweets without posting
python -m unittest
```
