#!/usr/bin/env python3
"""Shopping Spree — Flask shopping site.

Faithful replica of the provided shopping_spree.zip source. The "Flag" product is
only rendered for the `admin` user, but the /login route has a short-circuit logic
bug: `username and password and not any(...)` — if either field is falsy (e.g. an
empty password) the credential check never runs and the else-branch logs you in as
whatever username was submitted. So POSTing username=admin with an empty password
bypasses auth and reveals the flag product on /shop.

The flag comes from the FLAG env var (set by the generator from flags.env) — never
hard-coded. Listens on 0.0.0.0:5000 (matches `port: 5000` in challenge.yml). Templates
and CSS are inlined so the app stays a single file (the Dockerfile copies only app.py).
"""
from dataclasses import dataclass
import os

from flask import (
    Flask,
    render_template_string,
    request,
    redirect,
    url_for,
    session,
)

app = Flask(__name__)
app.secret_key = os.urandom(32).hex()

FLAG = os.environ.get("FLAG", "NZCSC{placeholder_set_the_real_flag_in_flags.env}")


@dataclass
class User:
    username: str
    password: str


# Temporary user storage. The admin password is random, so it cannot be guessed
# or brute-forced — the intended path is the login logic bug, not the password.
users: list[User] = [
    User(
        "admin",
        os.urandom(32).hex(),
    )
]


# Sample products
products = [
    {
        "name": "Laptop",
        "price": "$999",
        "image": "https://picsum.photos/300/200?1",
    },
    {
        "name": "Headphones",
        "price": "$199",
        "image": "https://picsum.photos/300/200?2",
    },
    {
        "name": "Phone",
        "price": "$799",
        "image": "https://picsum.photos/300/200?3",
    },
    {
        "name": f"Flag - {FLAG}",
        "price": "$1",
        "image": "https://cdn-icons-png.flaticon.com/512/2164/2164609.png",
    },
]


STYLE_CSS = """
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: Arial, sans-serif;
}

body {
  background: #f4f4f4;
}

.auth-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

.card {
  background: white;
  width: 100%;
  max-width: 400px;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}

.card h2 {
  text-align: center;
  margin-bottom: 20px;
}

input {
  width: 100%;
  padding: 12px;
  margin-bottom: 15px;
  border: 1px solid #ccc;
  border-radius: 8px;
}

button {
  width: 100%;
  padding: 12px;
  border: none;
  background: #007bff;
  color: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
}

button:hover {
  background: #0056b3;
}

.switch-link {
  text-align: center;
  margin-top: 15px;
}

.switch-link a {
  color: #007bff;
  text-decoration: none;
}

.error {
  color: red;
  text-align: center;
  margin-bottom: 15px;
}

.shop-container {
  max-width: 1200px;
  margin: auto;
  padding: 30px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.logout-btn {
  background: #dc3545;
  color: white;
  padding: 10px 18px;
  border-radius: 8px;
  text-decoration: none;
}

.products {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.product-card {
  background: white;
  padding: 20px;
  border-radius: 12px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.product-card img {
  width: 100%;
  height: 200px;
  object-fit: cover;
  border-radius: 8px;
  margin-bottom: 15px;
}

.product-card h3 {
  margin-bottom: 10px;
}

.product-card p {
  margin-bottom: 15px;
  font-size: 18px;
  font-weight: bold;
}
"""

BASE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>

  <title>{% block title %}{% endblock %}</title>

  <link
    rel="stylesheet"
    href="{{ url_for('static_style') }}"
  >
</head>
<body>

  {% block content %}{% endblock %}

</body>
</html>"""

LOGIN_HTML = """{% extends "base.html" %}

{% block title %}Login{% endblock %}

{% block content %}

<div class="auth-container">

  <div class="card">
    <h2>Login</h2>

    {% if error %}
      <p class="error">{{ error }}</p>
    {% endif %}

    <form method="POST">

      <input
        type="text"
        name="username"
        placeholder="Username"
        required
      >

      <input
        type="password"
        name="password"
        placeholder="Password"
        required
      >

      <button type="submit">Login</button>
    </form>

    <p class="switch-link">
      No account?
      <a href="{{ url_for('register') }}">Register</a>
    </p>
  </div>

</div>

{% endblock %}"""

REGISTER_HTML = """{% extends "base.html" %}

{% block title %}Register{% endblock %}

{% block content %}

<div class="auth-container">

  <div class="card">
    <h2>Register</h2>

    {% if error %}
      <p class="error">{{ error }}</p>
    {% endif %}

    <form method="POST">

      <input
        type="text"
        name="username"
        placeholder="Username"
        required
      >

      <input
        type="password"
        name="password"
        placeholder="Password"
        required
      >

      <button type="submit">Register</button>
    </form>

    <p class="switch-link">
      Already have an account?
      <a href="{{ url_for('login') }}">Login</a>
    </p>
  </div>

</div>

{% endblock %}"""

SHOP_HTML = """{% extends "base.html" %}

{% block title %}Shop{% endblock %}

{% block content %}

<div class="shop-container">

  <div class="topbar">
    <h1>Welcome, {{ username }}</h1>

    <a class="logout-btn" href="{{ url_for('logout') }}">
      Logout
    </a>
  </div>

  <div class="products">

    {% for product in products %}

    <div class="product-card">

      <img src="{{ product.image }}" alt="{{ product.name }}">

      <h3>{{ product.name }}</h3>

      <p>{{ product.price }}</p>

      <button>Add to Cart</button>

    </div>

    {% endfor %}

  </div>

</div>

{% endblock %}"""


@app.route("/static/style.css")
def static_style():
    # Serve the CSS byte-for-byte as the real challenge does: no leading or
    # trailing newline around the stylesheet body.
    return STYLE_CSS.strip(), 200, {"Content-Type": "text/css"}


def _render(template_src, **ctx):
    # Make "base.html" resolvable for {% extends %} while rendering inline strings.
    from jinja2 import DictLoader

    app.jinja_env.loader = DictLoader({"base.html": BASE_HTML})
    return render_template_string(template_src, **ctx)


@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("shop"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        assert username, password

        if username and password and not any(
            user.username == username and user.password == password
            for user in users
        ):
            error = "Invalid username or password"
        else:
            session["user"] = username
            return redirect(url_for("shop"))
    return _render(LOGIN_HTML, error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            error = "Invalid params"
        elif any(user.username == username for user in users):
            error = "User already exists"
        else:
            users.append(User(username, password))
            return redirect(url_for("login"))

    return _render(REGISTER_HTML, error=error)


@app.route("/shop")
def shop():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    if username == "admin":
        products_to_show = products
    else:
        # Non admin users don't see the flag :)
        products_to_show = list(filter(
            lambda x: "Flag" not in x["name"],
            products,
        ))

    return _render(
        SHOP_HTML,
        username=username,
        products=products_to_show,
    )


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
