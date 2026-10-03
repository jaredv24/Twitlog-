# Did we score 31?

A Twitter/X bot that, after every game, asks whether your college football team scored 31 points, and answers it. The answer is yes if they scored 31 or more:

```
Did Michigan score 31 points?

No.

Michigan 27, Rival 10
```

It runs for free on GitHub Actions. Every 30 minutes from Thursday to Sunday, it checks ESPN's public scoreboard. When a game has finished, it posts once. The IDs of games it has already posted are saved in `posted.json`.

## Setup

1. **Find your team's ESPN ID**
   ```
   python bot.py --search "Michigan"
   ```
   The ID is also the number in your team's ESPN URL, for example `espn.com/college-football/team/_/id/130/...`.

2. **Get X API keys.** Create an app at https://developer.x.com and set its permissions to **Read and write**. Then generate an API key and secret, plus an access token and secret, for the bot account.

3. **Configure the repo.** In GitHub, go to Settings → Secrets and variables → Actions:
   - Variables: `TEAM_ID` = your team's ID
   - Secrets: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`

4. **Skip games that were already played** so the bot doesn't post the whole season at once:
   ```
   TEAM_ID=130 python bot.py --backfill
   git commit -am "Backfill" && git push
   ```

## Local testing

```
pip install -r requirements.txt
TEAM_ID=130 python bot.py --dry-run   # prints tweets without posting
python -m unittest
```
