#!/usr/bin/env python3
import sys

from sqlalchemy import select, desc

from src import cheapshark
from src.db import Session
from src.models import Game, PriceSnapshot


def fetch(pages=2):
    deals = []
    for p in range(pages):
        batch = cheapshark.hit("deals", {"pageSize": 60, "pageNumber": p, "sortBy": "Deal Rating"})
        if not batch:
            break
        deals += batch
    return deals


def last_price(db, game_id, store_id):
    q = select(PriceSnapshot).where(
        PriceSnapshot.game_id == game_id,
        PriceSnapshot.store_id == store_id,
    ).order_by(desc(PriceSnapshot.collected_at)).limit(1)

    row = db.scalars(q).first()
    return row.price if row else None


def run(pages=2):
    deals = fetch(pages)
    print("pulled %d deals from cheapshark" % len(deals))

    db = Session()
    new_games = 0
    new_prices = 0
    unchanged = 0

    for d in deals:
        cs_id = d.get("gameID")
        if not cs_id:
            continue

        game = db.scalars(select(Game).where(Game.cheapshark_id == cs_id)).first()
        if game is None:
            game = Game(
                cheapshark_id=cs_id,
                title=d.get("title", "Unknown"),
                steam_app_id=d.get("steamAppID"),
                thumb=d.get("thumb"),
            )
            db.add(game)
            db.flush()  # need the id before we can attach a snapshot
            new_games += 1

        store = d.get("storeID")
        price = float(d.get("salePrice") or 0)
        normal = float(d.get("normalPrice") or 0)

        # only write a row when the price actually moved, otherwise every run
        # dumps another 120 identical rows and the history is useless
        if last_price(db, game.id, store) == price:
            unchanged += 1
            continue

        db.add(PriceSnapshot(
            game_id=game.id,
            store_id=store,
            price=price,
            normal_price=normal,
        ))
        new_prices += 1

    db.commit()

    total = db.query(PriceSnapshot).count()
    db.close()

    print("%d new games, %d price changes, %d unchanged" % (new_games, new_prices, unchanged))
    print("%d snapshots in the db now" % total)


if __name__ == "__main__":
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    run(pages)
