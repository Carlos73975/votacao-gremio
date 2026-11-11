import os, sqlite3, secrets, hashlib, csv, io
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, abort

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(APP_DIR, "votacao.db"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "troque-esta-senha")
SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-por-uma-chave-aleatoria")
CHAPAS = [
    "Jovens do Futuro",
    "Jovens para um Futuro",
    "As que vão se esforçar",
    "Geração Revolucionária",
]
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

def connect():
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    return db

def digest(value):
    return hashlib.sha256(value.strip().upper().encode("utf-8")).hexdigest()

def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS voter_codes (
            code_hash TEXT PRIMARY KEY,
            used INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS ballots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            choice TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('open','1')")

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]

@app.context_processor
def inject_globals():
    return {"csrf": csrf_token(), "chapas": CHAPAS}

@app.before_request
def check_csrf():
    if request.method == "POST":
        sent = request.form.get("csrf", "")
        if not sent or sent != session.get("csrf"):
            abort(400, "Sessão expirada. Atualize a página e tente novamente.")

def is_open(db=None):
    own = db is None
    db = db or connect()
    row = db.execute("SELECT value FROM settings WHERE key='open'").fetchone()
    if own: db.close()
    return bool(row and row["value"] == "1")

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper

@app.get("/")
def home():
    return render_template("home.html", opened=is_open())

@app.post("/vote")
def vote():
    code = request.form.get("code", "").strip()
    if not code:
        flash("Digite seu código de votação.", "error")
        return redirect(url_for("home"))
    db = connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        if not is_open(db):
            db.rollback()
            flash("A votação está encerrada.", "error")
            return redirect(url_for("home"))
        row = db.execute("SELECT code_hash, used FROM voter_codes WHERE code_hash=?", (digest(code),)).fetchone()
        if not row:
            db.rollback()
            flash("Código inválido. Confira e tente novamente.", "error")
            return redirect(url_for("home"))
        if row["used"]:
            db.rollback()
            flash("Este código já foi utilizado.", "error")
            return redirect(url_for("home"))
        session["vote_code_hash"] = row["code_hash"]
        return redirect(url_for("ballot"))
    finally:
        db.close()

@app.get("/ballot")
def ballot():
    if not session.get("vote_code_hash"):
        return redirect(url_for("home"))
    if not is_open():
        session.pop("vote_code_hash", None)
        flash("A votação está encerrada.", "error")
        return redirect(url_for("home"))
    return render_template("ballot.html")

@app.post("/cast")
def cast():
    choice = request.form.get("choice", "")
    code_hash = session.get("vote_code_hash")
    if choice not in CHAPAS or not code_hash:
        flash("Não foi possível validar a votação. Comece novamente.", "error")
        return redirect(url_for("home"))
    db = connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        if not is_open(db):
            db.rollback()
            flash("A votação foi encerrada.", "error")
            return redirect(url_for("home"))
        cur = db.execute("UPDATE voter_codes SET used=1 WHERE code_hash=? AND used=0", (code_hash,))
        if cur.rowcount != 1:
            db.rollback()
            session.pop("vote_code_hash", None)
            flash("Este código já foi utilizado ou não é válido.", "error")
            return redirect(url_for("home"))
        # A cédula não guarda o código do eleitor: o vínculo não é armazenado.
        db.execute("INSERT INTO ballots(choice, created_at) VALUES(?,?)",
                   (choice, datetime.now(timezone.utc).isoformat()))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    session.pop("vote_code_hash", None)
    return render_template("thanks.html")

@app.get("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    return redirect(url_for("dashboard"))

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if secrets.compare_digest(password, ADMIN_PASSWORD):
            session["admin"] = True
            return redirect(url_for("dashboard"))
        flash("Senha incorreta.", "error")
    return render_template("admin_login.html")

@app.post("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

@app.get("/admin/dashboard")
@admin_required
def dashboard():
    db = connect()
    counts = {c: db.execute("SELECT COUNT(*) n FROM ballots WHERE choice=?", (c,)).fetchone()["n"] for c in CHAPAS}
    total = sum(counts.values())
    unused = db.execute("SELECT COUNT(*) n FROM voter_codes WHERE used=0").fetchone()["n"]
    used = db.execute("SELECT COUNT(*) n FROM voter_codes WHERE used=1").fetchone()["n"]
    db.close()
    return render_template("dashboard.html", counts=counts, total=total, unused=unused, used=used, opened=is_open())

@app.post("/admin/codes")
@admin_required
def generate_codes():
    try:
        amount = int(request.form.get("amount", "0"))
    except ValueError:
        amount = 0
    if amount < 1 or amount > 1000:
        flash("Escolha uma quantidade entre 1 e 1000.", "error")
        return redirect(url_for("dashboard"))
    codes = []
    db = connect()
    for _ in range(amount):
        code = secrets.token_hex(4).upper()
        while db.execute("SELECT 1 FROM voter_codes WHERE code_hash=?", (digest(code),)).fetchone():
            code = secrets.token_hex(4).upper()
        db.execute("INSERT INTO voter_codes(code_hash,used) VALUES(?,0)", (digest(code),))
        codes.append(code)
    db.commit()
    db.close()
    session["new_codes"] = codes
    return redirect(url_for("show_codes"))

@app.get("/admin/codes")
@admin_required
def show_codes():
    codes = session.pop("new_codes", [])
    return render_template("codes.html", codes=codes)

@app.get("/admin/codes.csv")
@admin_required
def codes_csv():
    db = connect()
    rows = db.execute("SELECT used FROM voter_codes ORDER BY rowid").fetchall()
    db.close()
    # Os códigos são armazenados somente como hash e não podem ser recuperados.
    return Response("Código,Status\n", mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=codigos_votacao.csv"})

@app.post("/admin/toggle")
@admin_required
def toggle():
    db = connect()
    new_value = "0" if is_open(db) else "1"
    db.execute("UPDATE settings SET value=? WHERE key='open'", (new_value,))
    db.commit()
    db.close()
    flash("Votação encerrada." if new_value == "0" else "Votação aberta.", "success")
    return redirect(url_for("dashboard"))

@app.get("/admin/results.csv")
@admin_required
def results_csv():
    db = connect()
    rows = db.execute("SELECT choice, COUNT(*) AS votes FROM ballots GROUP BY choice").fetchall()
    db.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Chapa", "Votos", "Porcentagem"])
    result = {r["choice"]: r["votes"] for r in rows}
    total = sum(result.values())
    for c in CHAPAS:
        votes = result.get(c, 0)
        percentage = (votes / total * 100) if total else 0
        writer.writerow([c, votes, f"{percentage:.2f}%"])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=resultado_votacao.csv"})

@app.errorhandler(400)
def bad_request(error):
    return render_template("error.html", message=getattr(error, "description", "Requisição inválida.")), 400

init_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
