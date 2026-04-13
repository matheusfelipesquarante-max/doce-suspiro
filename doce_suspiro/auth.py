from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from functools import wraps
from database import conectar

from flask import Blueprint

auth = Blueprint("auth", __name__)


# -----------------------------
# DECORATOR LOGIN
# -----------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


# -----------------------------
# DECORATOR NÍVEL
# -----------------------------
def nivel_requerido(nivel_permitido):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get("nivel") != nivel_permitido:
                return "Acesso negado", 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# -----------------------------
# LOGIN
# -----------------------------
@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        nome = request.form["nome"]
        senha = request.form["senha"]

        conn = conectar()

        usuario = conn.execute("""
            SELECT * FROM usuarios
            WHERE nome = ?
        """, (nome,)).fetchone()

        conn.close()

        if usuario:
            session["usuario"] = usuario["nome"]
            session["nivel"] = usuario["nivel"]
            session["usuario_id"] = usuario["id"]

            # USUÁRIO DA LOJA (LEADPAGE)
            if usuario["nivel"] == 5:
                return redirect(url_for("loja"))

            # USUÁRIOS ADMIN
            return redirect(url_for("menu"))

        flash("Usuário ou senha inválidos", "erro")
        return render_template("login.html")

    return render_template("login.html")


# -----------------------------
# LOGOUT
# -----------------------------
@auth.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

