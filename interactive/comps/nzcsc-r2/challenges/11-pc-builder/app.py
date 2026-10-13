import os
import re
import secrets
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/pc_builder.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_NAME"] = "pc_builder_session"
app.config["SESSION_COOKIE_SECURE"] = True

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

csrf = CSRFProtect(app)

FLAG = os.environ.get("FLAG", "NZCSC{fake_flag_for_local_testing}")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminpass")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "bottoken")

STARTING_BALANCE = 1500
ADMIN_STARTING_BALANCE = 999_999_999_000_000

COMPONENTS = {
    "cpu":         {"label": "CPU",             "price": 350},
    "motherboard": {"label": "Motherboard",     "price": 200},
    "ram":         {"label": "Memory (RAM)",    "price": 1_000_000},
    "gpu":         {"label": "Graphics Card",   "price": 500},
    "storage":     {"label": "Storage (SSD)",   "price": 120},
    "psu":         {"label": "Power Supply",    "price": 90},
    "case":        {"label": "Case",            "price": 80},
    "cooler":      {"label": "CPU Cooler",      "price": 60},
}

TOTAL_BUILD_PRICE = sum(c["price"] for c in COMPONENTS.values())

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    balance = db.Column(db.Integer, nullable=False, default=STARTING_BALANCE)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    has_build = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PriceMatchRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    component = db.Column(db.String(30), nullable=False)
    claimed_price = db.Column(db.Integer, nullable=False)
    proof_url = db.Column(db.String(2048), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="price_match_requests")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def component_price_history():
    """Cosmetic data for the front page chart: memory prices climbing while
    everything else stays roughly flat."""
    return {
        "labels": ["Q1", "Q2", "Q3", "Q4", "Q1", "Q2", "Q3", "Q4"],
        "prices": [40, 45, 55, 70, 500, 15000, 250000, 1000000],
    }


def require_admin_bot():
    token = request.headers.get("X-Bot-Token", "")
    if not secrets.compare_digest(token, BOT_TOKEN):
        abort(403)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not USERNAME_RE.match(username):
            flash("Username must be 3-20 characters: letters, numbers, underscore.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("That username is already taken.", "error")
            return render_template("register.html")

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            balance=STARTING_BALANCE,
            is_admin=False,
        )
        db.session.add(user)
        db.session.commit()
        flash("Account created! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user is None or not check_password_hash(user.password_hash, password):
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        login_user(user)
        flash(f"Welcome back, {user.username}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("index"))


@app.route("/")
def index():
    return render_template(
        "index.html",
        chart_data=component_price_history(),
        components=COMPONENTS,
        total_price=TOTAL_BUILD_PRICE,
    )


@app.route("/dashboard")
@login_required
def dashboard():
    my_requests = (
        PriceMatchRequest.query
        .filter_by(user_id=current_user.id)
        .order_by(PriceMatchRequest.created_at.desc())
        .all()
    )
    flag = FLAG if current_user.has_build else None
    return render_template(
        "dashboard.html",
        total_price=TOTAL_BUILD_PRICE,
        components=COMPONENTS,
        my_requests=my_requests,
        flag=flag,
    )


@app.route("/shop")
@login_required
def shop():
    return render_template(
        "shop.html",
        components=COMPONENTS,
        total_price=TOTAL_BUILD_PRICE,
    )


@app.route("/build", methods=["POST"])
@login_required
def build():
    if current_user.has_build:
        flash("You already completed a build. Enjoy!", "success")
        return redirect(url_for("shop"))

    missing = [key for key in COMPONENTS if request.form.get(key) != "on"]
    if missing:
        labels = ", ".join(COMPONENTS[k]["label"] for k in missing)
        flash(f"Your build is missing critical component/s: {labels}.", "error")
        return redirect(url_for("shop"))

    if current_user.balance < TOTAL_BUILD_PRICE:
        flash("Not enough balance to complete this build.", "error")
        return redirect(url_for("shop"))

    current_user.balance -= TOTAL_BUILD_PRICE
    current_user.has_build = True
    db.session.commit()
    flash("Thanks for your order! Check your dashboard for your complimentary flag.", "success")
    return redirect(url_for("dashboard"))


@app.route("/price-match", methods=["GET", "POST"])
@login_required
def price_match():
    if request.method == "POST":
        component = request.form.get("component", "").strip()
        proof_url = request.form.get("proof_url", "").strip()
        claimed_price = request.form.get("claimed_price", "").strip()

        if component not in [component["label"] for component in COMPONENTS.values()]:
            flash("Please choose a valid component.", "error")
            return redirect(url_for("price_match"))

        if not proof_url.startswith(("http://", "https://")):
            flash("Proof URL must start with http:// or https://", "error")
            return redirect(url_for("price_match"))

        if not claimed_price.isdigit() or int(claimed_price) <= 0:
            flash("Claimed price must be a positive number.", "error")
            return redirect(url_for("price_match"))

        pm = PriceMatchRequest(
            user_id=current_user.id,
            component=component,
            claimed_price=int(claimed_price),
            proof_url=proof_url,
            status="pending",
        )
        db.session.add(pm)
        db.session.commit()
        flash("Thanks! Our team will review your price match request shortly.", "success")
        return redirect(url_for("dashboard"))

    return render_template("price_match.html", components=COMPONENTS)

@app.route("/review/<int:req_id>", methods=["POST"])
@login_required
@csrf.exempt
def review_price_match(req_id):
    if not current_user.is_admin:
        abort(403)

    pm = db.session.get(PriceMatchRequest, req_id)
    if pm is None:
        abort(404)

    if pm.status != "pending":
        return jsonify({"status": "ok", "message": f"Request already {pm.status}."})

    decision = request.values.get("decision", "deny")

    if decision == "approve":
        component_price =  next((c["price"] for c in COMPONENTS.values() if c["label"] == pm.component), None)
        credit = component_price - pm.claimed_price
        pm.user.balance += max(credit, 0)
        pm.status = "approved"
    else:
        pm.status = "denied"

    db.session.commit()
    return jsonify({"status": "ok", "decision": pm.status})

@app.route("/internal/pending", methods=["GET"])
def internal_pending():
    require_admin_bot()
    pending = PriceMatchRequest.query.filter_by(status="pending").all()
    return jsonify([
        {
            "id": p.id,
            "proof_url": p.proof_url,
            "component": p.component,
            "claimed_price": p.claimed_price,
        }
        for p in pending
    ])

@app.route("/internal/balance/<username>", methods=["GET"])
def internal_balance(username):
    require_admin_bot()
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    return jsonify({"username": user.username, "balance": user.balance})


def seed_admin():
    admin = User.query.filter_by(username="admin").first()
    if admin is None:
        admin = User(
            username="admin",
            password_hash=generate_password_hash(ADMIN_PASSWORD),
            balance=ADMIN_STARTING_BALANCE,
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()


with app.app_context():
    db.create_all()
    seed_admin()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
