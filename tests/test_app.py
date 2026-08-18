import pytest

from src import cheapshark
from src.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_serves_the_form(client):
    body = client.get("/").get_data(as_text=True)
    assert 'action="/echo_user_input"' in body
    assert 'name="user_input"' in body


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_input_is_echoed_back(client, monkeypatch):
    monkeypatch.setattr(cheapshark, "search_deals", lambda title, limit=12: [])
    body = client.post("/echo_user_input", data={"user_input": "Hollow Knight"}).get_data(as_text=True)
    assert "You entered: Hollow Knight" in body


def test_deals_are_listed(client, monkeypatch):
    deal = {
        "title": "Celeste",
        "store": "Steam",
        "sale_price": 4.99,
        "normal_price": 19.99,
        "savings": 75,
        "is_free": False,
        "url": "https://example.com/deal",
    }
    monkeypatch.setattr(cheapshark, "search_deals", lambda title, limit=12: [deal])
    body = client.post("/echo_user_input", data={"user_input": "celeste"}).get_data(as_text=True)
    assert "Celeste" in body
    assert "$4.99" in body
    assert "75%" in body


def test_empty_input_returns_to_the_form(client):
    body = client.post("/echo_user_input", data={"user_input": "   "}).get_data(as_text=True)
    assert "You entered:" not in body


def test_input_is_escaped(client, monkeypatch):
    monkeypatch.setattr(cheapshark, "search_deals", lambda title, limit=12: [])
    body = client.post("/echo_user_input", data={"user_input": "<script>alert(1)</script>"}).get_data(as_text=True)
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;" in body


def test_upstream_failure_still_echoes(client, monkeypatch):
    def boom(title, limit=12):
        raise RuntimeError("upstream down")

    monkeypatch.setattr(cheapshark, "search_deals", boom)
    body = client.post("/echo_user_input", data={"user_input": "Portal"}).get_data(as_text=True)
    assert "You entered: Portal" in body
    assert "Could not reach CheapShark" in body


def test_shape_maps_a_raw_deal():
    shaped = cheapshark._shape(
        {"title": "Braid", "storeID": "1", "salePrice": "2.50", "normalPrice": "10.00", "savings": "75.0", "dealID": "abc"},
        {"1": "Steam"},
    )
    assert shaped["store"] == "Steam"
    assert shaped["sale_price"] == 2.5
    assert shaped["savings"] == 75
    assert shaped["is_free"] is False
