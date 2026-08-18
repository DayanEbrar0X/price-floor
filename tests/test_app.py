import pytest

from src import cheapshark
from src.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def no_deals(title, limit=12):
    return []


def test_form_is_there(client):
    html = client.get("/").get_data(as_text=True)
    assert 'action="/echo_user_input"' in html
    assert 'name="user_input"' in html


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_it_echoes(client, monkeypatch):
    monkeypatch.setattr(cheapshark, "search_deals", no_deals)
    html = client.post("/echo_user_input", data={"user_input": "Hollow Knight"}).get_data(as_text=True)
    assert "You entered: Hollow Knight" in html


def test_deals_render(client, monkeypatch):
    fake = [{
        "title": "Celeste", "store": "Steam",
        "sale_price": 4.99, "normal_price": 19.99,
        "savings": 75, "is_free": False,
        "url": "https://example.com/deal",
    }]
    monkeypatch.setattr(cheapshark, "search_deals", lambda t, limit=12: fake)

    html = client.post("/echo_user_input", data={"user_input": "celeste"}).get_data(as_text=True)
    assert "Celeste" in html
    assert "$4.99" in html
    assert "75%" in html


def test_blank_input_just_goes_back(client):
    html = client.post("/echo_user_input", data={"user_input": "   "}).get_data(as_text=True)
    assert "You entered:" not in html


def test_no_script_injection(client, monkeypatch):
    monkeypatch.setattr(cheapshark, "search_deals", no_deals)
    html = client.post("/echo_user_input", data={"user_input": "<script>alert(1)</script>"}).get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_echoes_even_when_api_dies(client, monkeypatch):
    def dead(title, limit=12):
        raise RuntimeError("nope")

    monkeypatch.setattr(cheapshark, "search_deals", dead)
    html = client.post("/echo_user_input", data={"user_input": "Portal"}).get_data(as_text=True)
    assert "You entered: Portal" in html
    assert "Could not reach CheapShark" in html


def test_deal_parsing(monkeypatch):
    def fake_hit(path, params):
        if path == "stores":
            return [{"storeID": "1", "storeName": "Steam"}]
        return [{"title": "Braid", "storeID": "1", "salePrice": "2.50",
                 "normalPrice": "10.00", "savings": "75.0", "dealID": "abc"}]

    monkeypatch.setattr(cheapshark, "hit", fake_hit)
    cheapshark.store_cache.clear()

    d = cheapshark.search_deals("braid")[0]
    assert d["store"] == "Steam"
    assert d["sale_price"] == 2.5
    assert d["savings"] == 75
    assert d["is_free"] is False
