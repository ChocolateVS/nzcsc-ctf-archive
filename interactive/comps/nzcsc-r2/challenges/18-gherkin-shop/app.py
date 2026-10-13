import base64
import pickle
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for, make_response

app = Flask(__name__)


def read_flag() -> str:
    return Path("flag.txt").read_text().strip()


PRODUCTS = [
    ("Classic Gherkin", 3.50),
    ("Dill Pickle", 4.00),
    ("Kosher Dill", 4.50),
    ("Bread & Butter Chips", 3.80),
    ("Jar of Brine (refill)", 1.20),
]
PRICES = {name: price for name, price in PRODUCTS}


class Cart:
    def __init__(self):
        self.items = {}  # name -> [price, qty]

    def add(self, name: str, price: float, qty: int = 1):
        entry = self.items.get(name)
        if entry:
            entry[1] += qty
        else:
            self.items[name] = [price, qty]

    def total(self) -> float:
        return sum(price * qty for price, qty in self.items.values())


def load_cart():
    raw = request.cookies.get("cart")
    if not raw:
        return Cart()
    return pickle.loads(base64.b64decode(raw))


def save_cart(cart: Cart):
    blob = base64.b64encode(pickle.dumps(cart)).decode()
    resp = redirect(url_for("view_cart"))
    resp.set_cookie("cart", blob)
    return resp

def bad_cart(error: Exception):
    resp = make_response(render_template("bad_cart.html", error=error), 400)
    resp.delete_cookie("cart")
    return resp

@app.route("/")
def index():
    return render_template("shop.html", products=PRODUCTS)


@app.route("/add", methods=["POST"])
def add():
    try:
        cart = load_cart()
        name = request.form.get("name", "")
        qty = request.form.get("qty", "1")
        if name in PRICES:
            try:
                qty = max(1, min(99, int(qty)))
            except ValueError:
                qty = 1
            cart.add(name, PRICES[name], qty)
    except Exception as e:
        return bad_cart(e)
    return save_cart(cart)


@app.route("/cart")
def view_cart():
    try:
        cart = load_cart()
        lines = []
        for name, (price, qty) in cart.items.items():
            lines.append((str(name), price, qty, price * qty))
        return render_template("cart.html", lines=lines, total=cart.total())
    except Exception as e:
         return bad_cart(e)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
