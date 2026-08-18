import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

import collector
from src import cheapshark
from src.models import Base, Game, PriceSnapshot

DEAL = {
    "gameID": "612", "title": "Braid", "storeID": "1",
    "salePrice": "2.50", "normalPrice": "10.00",
    "steamAppID": "26800", "thumb": "http://x/y.jpg",
}


@pytest.fixture
def db(monkeypatch):
    # in-memory sqlite drops the db when the connection closes and the collector
    # opens its own session, so pin everything to one connection
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    S = sessionmaker(bind=engine)
    monkeypatch.setattr(collector, "Session", S)
    return S


def feed(monkeypatch, deals):
    calls = []

    def fake_hit(path, params):
        calls.append(params.get("pageNumber"))
        return deals if params.get("pageNumber") == 0 else []

    monkeypatch.setattr(cheapshark, "hit", fake_hit)


def test_it_saves_games_and_prices(db, monkeypatch):
    feed(monkeypatch, [DEAL])
    collector.run(pages=2)

    s = db()
    g = s.query(Game).one()
    assert g.title == "Braid"
    assert g.cheapshark_id == "612"
    assert g.steam_app_id == "26800"

    snap = s.query(PriceSnapshot).one()
    assert snap.price == 2.5
    assert snap.normal_price == 10.0
    assert snap.store_id == "1"
    assert snap.game_id == g.id
    s.close()


def test_running_twice_doesnt_duplicate(db, monkeypatch):
    feed(monkeypatch, [DEAL])
    collector.run(pages=1)
    collector.run(pages=1)

    s = db()
    assert s.query(Game).count() == 1
    assert s.query(PriceSnapshot).count() == 1
    s.close()


def test_new_row_when_price_moves(db, monkeypatch):
    feed(monkeypatch, [DEAL])
    collector.run(pages=1)

    cheaper = dict(DEAL, salePrice="1.25")
    feed(monkeypatch, [cheaper])
    collector.run(pages=1)

    s = db()
    assert s.query(Game).count() == 1
    prices = sorted(p.price for p in s.query(PriceSnapshot).all())
    assert prices == [1.25, 2.5]
    s.close()


def test_deal_with_no_game_id_is_skipped(db, monkeypatch):
    feed(monkeypatch, [{"title": "junk", "storeID": "1", "salePrice": "1.00", "normalPrice": "2.00"}])
    collector.run(pages=1)

    s = db()
    assert s.query(Game).count() == 0
    s.close()


def test_last_price_is_none_for_new_game(db):
    s = db()
    assert collector.last_price(s, 999, "1") is None
    s.close()
