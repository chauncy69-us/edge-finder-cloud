# Edge Finder Cloud 4.1 — NFL + UFC

**Deployable website source — not a live public site until you publish it to GitHub Pages.**

Edge Finder Cloud is a browser-based research pilot that preserves the Edge Finder 4 NFL props, NFL matchup, UFC fighter comparison, candidate search, walk-forward validation, and separate research journal workflows. It is built for a **public GitHub Pages site** with **twice-daily GitHub Actions historical-data refresh attempts**. There are no file downloads or installation steps for people using the published URL.

## Easiest Windows setup (GitHub Desktop)

1. Create/sign in to your own **GitHub account** at https://github.com.
2. Install **GitHub Desktop** from https://desktop.github.com if you don't already have it.
3. Create a new **public** GitHub repository called `edge-finder-cloud` with the default branch `main`. If GitHub offers to initialize it with a README, you may do so.
4. In GitHub Desktop, choose **File → Clone repository** and clone `edge-finder-cloud` to your Documents folder.
5. Extract this ZIP. **Copy the contents** of the `Edge_Finder_Hosted` folder — including the `.github` directory — into the **root of your cloned repository**. Do **not** copy the `Edge_Finder_Hosted` folder itself as a nested directory.
6. Back in GitHub Desktop, enter the summary `Deploy Edge Finder Cloud`, select **Commit to main**, then **Push origin**.
7. In your GitHub repository website, go to **Settings → Pages → Build and deployment → Source: GitHub Actions**. GitHub may require you to save the setting.
8. Open the repository **Actions** tab. Choose **Refresh and deploy Edge Finder**, then **Run workflow**. Review any warnings in the build log.
9. Return to **Settings → Pages** and click **Visit site**. A typical published URL is `https://YOUR-USERNAME.github.io/edge-finder-cloud/` (your real address is assigned by GitHub; don't assume this example is active).
10. Bookmark the website in Chrome or on your phone. After that, data refreshes run on the host. No Windows batch file or CSV update needed for normal use.

**Important:** If your newly created default branch is not `main`, adjust `.github/workflows/refresh-and-deploy.yml` to match it before publishing.

## Using the research app

- **NFL Props:** Pick season and week, select a team and quarterback/receiver, enter Bet365 American odds, review estimated win probability and sensitivity; it is *not* an independently validated positive-EV model.
- **NFL Matchups:** Compare historical team scores and outcomes. Matchup view is descriptive only.
- **UFC Fights:** Compare two fighters with dated decisive historical UFC bouts and an experimental Elo/form model; enter sportsbook odds manually.
- **NFL Candidates:** Find historical player-prop thresholds to price check yourself.
- **NFL Validation:** Run a chronological statistical audit; it does not prove betting profitability without historical tradable quotes.
- **NFL / UFC journals:** Save pre-event research records and grade outcomes afterward. Saved locally in your current browser. **Use Data & Settings → Backup all research journals** regularly.
- **Data & Settings:** See most recent downloaded NFL week, dated UFC result, refresh time and warnings. Manual CSV import is preserved as a fallback.

## Data refresh design

`.github/workflows/refresh-and-deploy.yml` runs on repository changes, manual request, and approximately **11:25 and 22:25 UTC daily**. GitHub's schedule is best-effort, may be delayed or disabled after 60 days of inactivity in a public repository, and is not real-time.

`python scripts/refresh_data.py` downloads and validates:

| Feed | Location | Expected behavior |
|---|---|---|
| NFL player game logs, 2020–current season | `nflverse/nflverse-data` GitHub releases `stats_player` | nflverse generally updates following NFL game days; availability/corrections subject to upstream. |
| NFL game schedules/results | `nflverse/nflverse-data` release `schedules/games.csv` | May update separately from player game logs. |
| UFC fight-history primary | `Greco1899/scrape_ufc_stats` (`ufc_fight_results.csv` plus `ufc_event_details.csv`) | A third-party GitHub dataset describing daily incremental scraping from UFCStats. Frequency is not guaranteed. |
| UFC fight-history fallback | `larissapavan/ufc-historical-fight-dataset` | Secondary historical snapshot. Might be stale; the newest validated dated source wins. |

- Datasets are checked for plausible CSV structures and sufficient records; malformed responses are rejected.
- GitHub Actions attempts to restore the previous verified files from a build cache when a source is temporarily unavailable; caches are best-effort and can expire or be evicted. If there is no prior usable cache, the UI clearly indicates missing data.
- A source successfully downloaded **does not guarantee a recent match or fight has been ingested**. Check the displayed latest game-week and UFC event date before using the estimates.
- UFC fights without a recognizable winner and trustworthy date are excluded; draws/no-contests are not counted as wins.
- The publisher does **not** automatically access Bet365, live odds, injuries, weather, confirmed lineups, or UFC fight cards. Do not assume sportsbook prices are historical or tradable.
- GitHub Pages is static hosting. Personal bets are **not synced across phones/computers**, and the app has **no user account system or private server-side database**.
- The repository and site are **public** under GitHub Free. Do not commit sportsbook accounts, credentials, personal betting history, API keys or sensitive documents. Data sources may have terms or copyright requirements; review before commercial/public redistribution. Give credit to nflverse and other providers.

## Operational controls

In your GitHub repository: **Actions → Refresh and deploy Edge Finder → Run workflow** performs an immediate source check and deployment. If a build fails, inspect logs before relying on old data. Github-hosted scheduled Actions may be delayed, disabled after lengthy repository inactivity, or blocked by account limits. Set calendar reminders to periodically check the Actions health, especially during NFL season.

For significantly stronger reliability, private cloud journals, synchronized devices, paid historical odds, live data, or push alerts, you would need a backend with authentication, licensed provider integrations and monitoring (e.g., Cloudflare Workers plus managed DB, or a managed service). This free tier is **not** that subscription platform.

## Developer check

From the repo root, run `python -m unittest discover -s tests -v`. Optional manual refresh: `python scripts/refresh_data.py` (requires internet access). No additional Python packages required.

## Credentials and safety

No Bet365 credentials, no passwords, no automatic wagers. EV estimates are exploratory, not promises of profit. Review each source's data provenance and refresh date and check injuries / fight status at the sportsbook before acting.
