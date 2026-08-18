from flask import Flask, render_template, request

from src import cheapshark

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", query=None, deals=None, error=None)


@app.route("/echo_user_input", methods=["POST"])
def echo_user_input():
    text = request.form.get("user_input", "").strip()
    if not text:
        return render_template("index.html", query=None, deals=None, error=None)

    deals = []
    err = None
    try:
        deals = cheapshark.search_deals(text)
    except Exception:
        # cheapshark goes down sometimes and the whole point of the page is
        # echoing the input back, so don't let their outage take us with it
        err = "Could not reach CheapShark just now. The search above was received; try again in a moment."

    return render_template("index.html", query=text, deals=deals, error=err)


@app.route("/health")
def health():
    return {"status": "ok"}
