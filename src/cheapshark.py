import os

import requests

BASE = "https://www.cheapshark.com/api/1.0"
# they reject you with a generic UA, took me a while to figure that out.
# real contact goes in CONTACT_EMAIL on the server, this default is a throwaway
UA = "PriceFloor/0.1 (%s)" % os.environ.get("CONTACT_EMAIL", "devuser1799@gmail.com")

store_cache = {}


def hit(path, params):
    r = requests.get(BASE + "/" + path, params=params,
                     headers={"User-Agent": UA}, timeout=8)
    r.raise_for_status()
    return r.json()


def get_stores():
    if not store_cache:
        for s in hit("stores", {}):
            store_cache[s["storeID"]] = s["storeName"]
    return store_cache


def search_deals(title, limit=12):
    raw = hit("deals", {"title": title, "pageSize": limit, "sortBy": "Savings"})
    stores = get_stores()

    out = []
    for d in raw:
        sale = float(d.get("salePrice") or 0)
        was = float(d.get("normalPrice") or 0)

        out.append({
            "title": d.get("title", "Unknown"),
            "store": stores.get(d.get("storeID"), "Unknown store"),
            "sale_price": sale,
            "normal_price": was,
            "savings": round(float(d.get("savings") or 0)),
            "is_free": sale == 0,
            "url": "https://www.cheapshark.com/redirect?dealID=" + d.get("dealID", ""),
        })

    return out
