# Price Floor

A game-deal tracker that judges a sale against the game's own price history instead of its advertised discount.

Course project. This README is the working record: what we said we'd build, what's decided, what's left.

---

## Product description (assignment paragraph)

Price Floor is aimed at a small but real frustration: PC game prices swing constantly across a dozen storefronts, and a banner reading "75% off" tells a shopper nothing about whether that price is actually good or just back to where it sat two months ago. The product pulls deal listings from CheapShark's public API on a schedule, records every price it sees, and compares today's price against each game's own stored history, so it can say plainly whether a sale is a genuine low or routine noise. It is built for budget-minded PC gamers and students who keep a wishlist and are willing to wait for the right moment to buy, rather than for collectors chasing new releases at launch. What separates it from the store pages and deal aggregators it draws from is that it does not rank deals by advertised discount at all — it keeps its own price record over time and scores each deal against that record, so a game marked down 20% from a price that has never dropped before is surfaced ahead of one marked down 75% from an inflated list price nobody has paid in a year.

Answers the three required questions in order: the problem, the audience, what makes it different.

---

## Architecture

```
                  CheapShark API
                  public JSON, no key
                        |  ^
     GET /deals, every 6h  |  |  JSON listings
                        v  |
  +---------------------------------------------------------------+
  |  BACK END - server side, no direct user access                 |
  |                                                                |
  |   Collector  --writes price rows-->  PostgreSQL                |
  |   python worker                      games                     |
  |   cron, 6h timer                     price_snapshots           |
  |                                        |  ^                    |
  |                    reads 90-day history|  |writes deal score   |
  |                                        v  |                    |
  |                                      Analyzer                  |
  |                                      python worker             |
  |                                      runs after each pull      |
  |                                                                |
  |                     PostgreSQL                                 |
  |                        |  ^                                    |
  |         SELECT scored  |  | rows                               |
  |                        v  |                                    |
  |                      REST API                                  |
  |                      FastAPI, read-only                        |
  +---------------------------------------------------------------+
                           |  ^
   GET /api/deals?store=&under=  |  JSON: deals + price history
                           v  |
  +---------------------------------------------------------------+
  |  FRONT END - what the user touches                             |
  |                      Web UI                                    |
  |                      React in the browser                      |
  +---------------------------------------------------------------+
```

The proper diagram lives in `price-floor.html` — that's the one to submit.

Two things the diagram is built to make obvious, because they're what the assignment is graded on:

- **Collection and analysis are separate processes.** They never call each other. The collector only talks to the network, the analyzer only talks to the database, and they hand off through Postgres.
- **The front end reaches the back end only through the REST API.** No direct database access from the browser, ever.

---

## Components

| Component | Side | Responsibility |
|---|---|---|
| Collector | Back end | Wakes on a six-hour timer, calls CheapShark, writes one row per game per price it sees. Never analyzes anything. |
| PostgreSQL | Back end | Game catalog, every price snapshot ever collected, and the analyzer's output. The only thing the two workers share. |
| Analyzer | Back end | Reads each game's stored history, computes all-time low, 90-day median, and a deal score for the current price. Never touches the network. |
| REST API | Back end | Read-only JSON over the scored results. The single boundary between front end and everything behind it. |
| Web UI | Front end | Filter by store and budget, sort a deal table by score, open a game to see its price chart. Talks only to the REST API. |

---

## Data source

CheapShark. No API key, no signup, no OAuth — the reason we picked it over the job-board and used-car ideas.

The one requirement: send a descriptive User-Agent or it rejects you.

```
curl -A "PriceFloor/0.1 (student project; devuser1799@gmail.com)" \
  "https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=15&pageSize=5"
```

Endpoints we need:

- `/api/1.0/deals` — the main list, paginated, filterable by store and price
- `/api/1.0/stores` — store IDs to names, fetched once and cached
- `/api/1.0/games?ids=` — batch lookup by game ID

Verified working before we committed to it. Fields that matter per listing: `gameID`, `title`, `storeID`, `salePrice`, `normalPrice`, `steamAppID`, `thumb`.

---

## Schema sketch

Built, see the Schema section above. The `deals` table lands with the analyzer:

```
deals
  game_id, store_id, current_price, all_time_low, median_90d, score, updated_at
```

---

## API surface

```
GET /api/stores
GET /api/deals?store=&under=&min_score=&sort=
GET /api/games/{id}          -> game detail + full price history for the chart
```

Read-only. Nothing in the front end writes.

---

## Deal score

The part that makes this project not just another aggregator. Rough shape, to be tuned once we have real history:

- How far below the 90-day median is the current price
- How close it is to the all-time low we've recorded
- How rare a drop this size is for this game

A 20% cut on a game that has never gone on sale should beat a 75% cut on a game permanently discounted from a fake list price.

Note: this needs collected history to mean anything. The first run has nothing to compare against, so we start the collector early and let it accumulate while we build the rest.

---

## Running it locally

```
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
flask --app src.app run
```

Then open http://127.0.0.1:5000. Tests: `pytest`.

Routes:

- `GET /` — the search form
- `POST /echo_user_input` — echoes the input back, then lists matching deals
- `GET /health` — returns `{"status": "ok"}`, used as a deploy smoke check

## Database and the collector

SQLite by default, so the whole thing runs with no server to install. Set `DATABASE_URL` to a Postgres URL and the same code points at Postgres instead — nothing else changes.

Set up the schema and pull some prices:

```
pip install -r requirements-dev.txt
alembic upgrade head
python collector.py
```

`collector.py` is the separate data-collection process from the architecture diagram. It pulls the current top deals from CheapShark, adds any game it has not seen before, and writes a price snapshot. It only writes a row when the price actually moved — otherwise every run would dump another 120 identical rows and the history would be worthless.

Sample run:

```
pulled 120 deals from cheapshark
92 new games, 120 price changes, 0 unchanged
120 snapshots in the db now
```

Run it again straight away and it reports `0 new games, 0 price changes, 120 unchanged`.

Scheduling, once it lives on a server:

```
0 */6 * * * cd /path/to/price-floor && ./venv/bin/python collector.py >> collector.log 2>&1
```

Migrations are Alembic, in `migrations/versions/`. After changing anything in `src/models.py`:

```
alembic revision --autogenerate -m "what changed"
alembic upgrade head
```

## Schema

```
games
  id, cheapshark_id (unique), title, steam_app_id, thumb, first_seen

price_snapshots
  id, game_id -> games.id, store_id, price, normal_price, collected_at
  index on (game_id, store_id)
```

`price_snapshots` is append-only. It is the history the deal score gets derived from, so nothing overwrites it.

## Deployment

Hosted on Vercel, connected to this GitHub repo. Every push to `main` deploys automatically.

- `api/index.py` is the entry point Vercel looks for; it imports the Flask app.
- `vercel.json` routes all paths to that function and tells the bundler to include the Jinja templates, which are not picked up automatically because nothing imports them.
- `Procfile` is left in place so the app still runs under gunicorn anywhere else. Vercel ignores it.

GitHub Actions runs the test suite on every push and pull request to `main`. Config in `.github/workflows/ci.yml`.

## Status

- [x] Pick the project, confirm the data source works
- [x] Write the assignment paragraph
- [x] Architecture diagram
- [x] Submit milestone 1
- [x] Flask app that echoes user input
- [x] Live CheapShark search wired into the echo
- [x] Test suite, 8 tests
- [x] GitHub repo and CI
- [x] Deploy to Vercel, submit the public URL
- [x] Schema and migrations
- [x] Collector worker
- [ ] Analyzer worker and scoring
- [ ] REST API
- [ ] Web UI: deal table and filters
- [ ] Web UI: price history chart

---

## Notes

- Repo: https://github.com/DayanEbrar0X/price-floor
- The deployed web app still reads CheapShark live on each request. It is not wired to the database yet, on purpose: Vercel's filesystem is ephemeral, so a SQLite file written there would not survive. The collector runs locally against its own database. Pointing both at a hosted Postgres is the next deploy step.
- SQLite instead of Postgres for now. The README originally said Postgres, but a grader should be able to unzip this and run it without installing a database server. `DATABASE_URL` switches it over with no code change.
- Heroku dropped its free tier in November 2022, so we deployed on Vercel instead. The grading criteria asks for a public URL, not a specific host.
- Single data source on purpose. Multi-store collection means reconciling game titles across stores, which is a real problem but not the one this assignment grades. If more collection surface is wanted, a second collector process drops into the existing shape without changing anything else.
- Rendered submission page: https://claude.ai/code/artifact/42be8cf1-9515-454b-acac-c5ceb957ae23
- The page was published from the repo root before being moved here. To update it from this path, pass that URL explicitly or it'll create a second artifact instead of replacing the first.
