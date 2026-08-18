import requests

BASE = "https://www.cheapshark.com/api/1.0"
USER_AGENT = "PriceFloor/0.1 (student project; devuser1799@gmail.com)"
TIMEOUT = 8

_stores = {}


def _get(path, params):
    response = requests.get(
        f"{BASE}/{path}",
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def store_names():
    global _stores
    if not _stores:
        _stores = {s["storeID"]: s["storeName"] for s in _get("stores", {})}
    return _stores


def search_deals(title, limit=12):
    raw = _get("deals", {"title": title, "pageSize": limit, "sortBy": "Savings"})
    stores = store_names()
    return [_shape(deal, stores) for deal in raw]


def _shape(deal, stores):
    sale = float(deal.get("salePrice") or 0)
    normal = float(deal.get("normalPrice") or 0)
    return {
        "title": deal.get("title", "Unknown"),
        "store": stores.get(deal.get("storeID"), "Unknown store"),
        "sale_price": sale,
        "normal_price": normal,
        "savings": round(float(deal.get("savings") or 0)),
        "is_free": sale == 0,
        "url": f"https://www.cheapshark.com/redirect?dealID={deal.get('dealID', '')}",
    }
