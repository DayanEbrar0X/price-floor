from flask import Flask, render_template, request

from src import cheapshark

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", query=None, deals=None, error=None)


@app.route("/echo_user_input", methods=["POST"])
def echo_user_input():
    query = request.form.get("user_input", "").strip()
    if not query:
        return render_template("index.html", query=None, deals=None, error=None)

    try:
        deals = cheapshark.search_deals(query)
        error = None
    except Exception:
        deals = []
        error = "Could not reach CheapShark just now. The search above was received; try again in a moment."

    return render_template("index.html", query=query, deals=deals, error=error)


@app.route("/health")
def health():
    return {"status": "ok"}
