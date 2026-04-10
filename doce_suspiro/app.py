import sqlite3
from config import Config
from auth import auth, login_required, nivel_requerido
from flask import Flask, render_template, request, redirect, session, url_for, flash
from database import conectar, criar_tabelas
from functools import wraps
from datetime import datetime, date
import webbrowser
import threading
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, mm
from reportlab.lib.units import inch, mm
from flask import send_file
from io import BytesIO
from werkzeug.utils import secure_filename
from licenca import verificar_licenca
import sys

criar_tabelas()
verificar_licenca()
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


app = Flask(__name__, template_folder="templates")
app.config.from_object(Config)
app.register_blueprint(auth)

# -----------------------------
# Decorator de Nível
# -----------------------------
def nivel_requerido(*niveis_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get("nivel") not in niveis_permitidos:
                return "Acesso negado", 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# -----------------------------
# Login
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nome = request.form["nome"].upper()
        senha = request.form["senha"].upper()

        conn = conectar()
        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE nome = ? AND senha = ?",
            (nome, senha)
        ).fetchone()
        conn.close()

        if usuario:
            session["usuario"] = usuario["nome"]
            session["nivel"] = usuario["nivel"]
            session["usuario_id"] = usuario["id"] 
            return redirect(url_for("loja"))
        else:
            return "Usuário ou senha inválidos"

    return render_template("login.html")

# -----------------------------
# Menu
# -----------------------------
@app.route("/menu")
@login_required
@nivel_requerido(1)
def menu():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM pedidos_online
        WHERE status = 'NOVO'
    """)

    pedidos_novos = conn.execute("""
    SELECT COUNT(*) FROM pedidos_online
    WHERE status = 'NOVO'
    """).fetchone()[0]

    conn.close()

    return render_template(
        "menu.html",
        pedidos_novos=pedidos_novos
    )
    
# -----------------------------
# Cadastro de Usuários
# -----------------------------
@app.route("/usuarios", methods=["GET", "POST"])
@login_required
@nivel_requerido(1)
def usuarios():

    conn = conectar()

    if request.method == "POST":

        nome = request.form["nome"].upper()
        usuario = request.form["usuario"].upper()
        senha = request.form["senha"].upper()
        celular = request.form.get("celular")
        endereco = request.form.get("endereco")
        nivel = int(request.form["nivel"])

        try:

            conn.execute("""
            INSERT INTO usuarios
            (nome, usuario, senha, celular, endereco, nivel)
            VALUES (?, ?, ?, ?, ?, ?)
            """,(nome, usuario, senha, celular, endereco, nivel))

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()
            return "Usuário já existe."

    lista_usuarios = conn.execute("""
    SELECT * FROM usuarios ORDER BY id
    """).fetchall()

    conn.close()

    return render_template(
        "usuarios.html",
        usuarios=lista_usuarios
    )

# -----------------------------
# Logout
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.logout"))


# -----------------------------
# CLIENTES
# -----------------------------
@app.route("/clientes", methods=["GET", "POST"])
@login_required
def clientes():

    conn = conectar()

    # CADASTRAR CLIENTE
    if request.method == "POST":
        nome = request.form["nome"].upper()
        telefone = request.form["telefone"].upper()
        documento = request.form["documento"].upper()
        endereco = request.form["endereco"].upper()

        conn.execute("""
            INSERT INTO clientes (nome, telefone, documento, endereco)
            VALUES (?, ?, ?, ?)
        """, (nome, telefone, documento, endereco))

        conn.commit()

    lista_clientes = conn.execute("SELECT * FROM clientes ORDER BY nome").fetchall()
    conn.close()

    return render_template("clientes.html", clientes=lista_clientes)

@app.route("/editar_cliente/<int:id>", methods=["GET", "POST"])
@login_required
def editar_cliente(id):

    conn = conectar()

    if request.method == "POST":
        nome = request.form["nome"].upper()
        telefone = request.form["telefone"].upper()
        documento = request.form["documento"].upper()
        endereco = request.form["endereco"].upper()

        conn.execute("""
            UPDATE clientes
            SET nome = ?, telefone = ?, documento = ?, endereco = ?
            WHERE id = ?
        """, (nome, telefone, documento, endereco, id))

        conn.commit()
        conn.close()

        return redirect(url_for("clientes"))

    cliente = conn.execute("SELECT * FROM clientes WHERE id = ?", (id,)).fetchone()
    conn.close()

    return render_template("editar_cliente.html", cliente=cliente)

@app.route("/excluir_cliente/<int:id>")
@login_required
def excluir_cliente(id):

    conn = conectar()
    conn.execute("DELETE FROM clientes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("clientes"))

# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():

    conn = conectar()

    # =========================
    # FILTROS
    # =========================
    cliente_id = request.args.get("cliente")
    produto_id = request.args.get("produto")
    data_inicio = request.args.get("inicio")
    data_fim = request.args.get("fim")

    where = []
    params = []

    if cliente_id:
        where.append("v.cliente_id = ?")
        params.append(cliente_id)

    if data_inicio and data_fim:
        where.append("date(v.data) BETWEEN ? AND ?")
        params.append(data_inicio)
        params.append(data_fim)

    filtro_vendas = ""
    if where:
        filtro_vendas = "WHERE " + " AND ".join(where)

    # =========================
    # FATURAMENTO
    # =========================
    faturamento_total = conn.execute(f"""
        SELECT IFNULL(SUM(v.valor_total),0) as total
        FROM vendas v
        {filtro_vendas}
    """, params).fetchone()["total"]

    total_vendas = conn.execute(f"""
        SELECT COUNT(*) as total
        FROM vendas v
        {filtro_vendas}
    """, params).fetchone()["total"]

    ticket_medio = faturamento_total / total_vendas if total_vendas else 0

    # =========================
    # VENDAS POR MÊS
    # =========================
    vendas_mes = conn.execute(f"""
        SELECT strftime('%Y-%m', v.data) as mes,
               SUM(v.valor_total) as total
        FROM vendas v
        {filtro_vendas}
        GROUP BY mes
        ORDER BY mes
    """, params).fetchall()
    vendas_labels = []
    vendas_data = []

    for v in vendas_mes:
        vendas_labels.append(v["mes"])
        vendas_data.append(v["total"])

    # =========================
    # TOP 5 PRODUTOS
    # =========================
    where_prod = []
    params_prod = []

    if produto_id:
        where_prod.append("vi.produto_id = ?")
        params_prod.append(produto_id)

    if cliente_id:
        where_prod.append("v.cliente_id = ?")
        params_prod.append(cliente_id)

    if data_inicio and data_fim:
        where_prod.append("date(v.data) BETWEEN ? AND ?")
        params_prod.append(data_inicio)
        params_prod.append(data_fim)

    filtro_prod = ""
    if where_prod:
        filtro_prod = "WHERE " + " AND ".join(where_prod)

    top_produtos = conn.execute(f"""
        SELECT p.nome, SUM(vi.quantidade) as total
        FROM venda_itens vi
        JOIN vendas v ON v.id = vi.venda_id
        JOIN produtos p ON p.id = vi.produto_id
        {filtro_prod}
        GROUP BY vi.produto_id
        ORDER BY total DESC
        LIMIT 5
    """, params_prod).fetchall()

    # =========================
    # TOP 5 CLIENTES
    # =========================
    top_clientes = conn.execute(f"""
        SELECT c.nome, SUM(v.valor_total) as total
        FROM vendas v
        JOIN clientes c ON c.id = v.cliente_id
        {filtro_vendas}
        GROUP BY v.cliente_id
        ORDER BY total DESC
        LIMIT 5
    """, params).fetchall()

    # =========================
    # PRODUTO MAIS / MENOS
    # =========================
    produto_mais = conn.execute(f"""
        SELECT p.nome, SUM(vi.quantidade) as total
        FROM venda_itens vi
        JOIN vendas v ON v.id = vi.venda_id
        JOIN produtos p ON p.id = vi.produto_id
        {filtro_prod}
        GROUP BY vi.produto_id
        ORDER BY total DESC
        LIMIT 1
    """, params_prod).fetchone()

    produto_menos = conn.execute(f"""
        SELECT p.nome, SUM(vi.quantidade) as total
        FROM venda_itens vi
        JOIN vendas v ON v.id = vi.venda_id
        JOIN produtos p ON p.id = vi.produto_id
        {filtro_prod}
        GROUP BY vi.produto_id
        ORDER BY total ASC
        LIMIT 1
    """, params_prod).fetchone()

    # =========================
    # TOTAL PRODUTOS
    # =========================
    total_produtos = conn.execute("""
        SELECT COUNT(*) as total FROM produtos
    """).fetchone()["total"]

    # =========================
    # VALOR DO ESTOQUE
    # =========================
    valor_estoque = conn.execute("""
        SELECT IFNULL(SUM(
            (
                SELECT IFNULL(SUM(
                    CASE 
                        WHEN tipo = 'ENTRADA' THEN quantidade
                        ELSE -quantidade
                    END
                ),0)
                FROM estoque_movimentacoes
                WHERE produto_id = p.id
            ) * p.preco
        ),0) as total
        FROM produtos p
    """).fetchone()["total"]

    # =========================
    # ALERTA ESTOQUE
    # =========================
    alerta_estoque = conn.execute("""
        SELECT p.nome,
               IFNULL(SUM(
                   CASE
                       WHEN em.tipo = 'ENTRADA' THEN em.quantidade
                       ELSE -em.quantidade
                   END
               ),0) as saldo
        FROM produtos p
        LEFT JOIN estoque_movimentacoes em
        ON p.id = em.produto_id
        GROUP BY p.id
        HAVING saldo <= 5
    """).fetchall()

    # =========================
    # LISTAS PARA FILTRO
    # =========================
    clientes = conn.execute("SELECT * FROM clientes ORDER BY nome").fetchall()
    produtos = conn.execute("SELECT * FROM produtos ORDER BY nome").fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        clientes=clientes,
        produtos=produtos,
        cliente_selecionado=cliente_id,
        produto_selecionado=produto_id,
        inicio=data_inicio,
        fim=data_fim,
        faturamento_total=faturamento_total,
        ticket_medio=ticket_medio,
        total_produtos=total_produtos,
        valor_estoque=valor_estoque,
        top_clientes=top_clientes,
        alerta_estoque=alerta_estoque,
        produto_mais=produto_mais,
        produto_menos=produto_menos,
        vendas_labels=vendas_labels,
        vendas_data=vendas_data,
        now=datetime.now()
    )
# -----------------------------
# ESTOQUE
# -----------------------------
@app.route("/estoque", methods=["GET", "POST"])
@login_required
def estoque():

    conn = conectar()

    # MOVIMENTAÇÃO
    if request.method == "POST":
        produto_id = request.form["produto_id"]
        tipo = request.form["tipo"]
        quantidade = int(request.form["quantidade"])

        conn.execute("""
            INSERT INTO estoque_movimentacoes (produto_id, tipo, quantidade)
            VALUES (?, ?, ?)
        """, (produto_id, tipo, quantidade))

        conn.commit()

    # LISTAR PRODUTOS
    produtos = conn.execute("SELECT * FROM produtos ORDER BY nome").fetchall()

    # HISTÓRICO + NOME DO PRODUTO
    movimentacoes = conn.execute("""
        SELECT 
            em.id,
            em.tipo,
            em.quantidade,
            em.data,
            p.nome as nome_produto,
            (
                SELECT 
                    SUM(
                        CASE 
                            WHEN tipo = 'ENTRADA' THEN quantidade
                            ELSE -quantidade
                        END
                    )
                FROM estoque_movimentacoes
                WHERE produto_id = p.id
            ) as saldo_atual
        FROM estoque_movimentacoes em
        JOIN produtos p ON p.id = em.produto_id
        ORDER BY em.data DESC
    """).fetchall()

    conn.close()

    return render_template(
        "estoque.html",
        produtos=produtos,
        movimentacoes=movimentacoes
    )
# -----------------------------
# PRODUTOS
# -----------------------------

@app.route("/produtos", methods=["GET", "POST"])
@login_required
def produtos():

    conn = conectar()

    if request.method == "POST":

        nome = request.form["nome"].upper()
        preco = float(request.form["preco"])

        try:

            conn.execute("""
                INSERT INTO produtos (nome, preco)
                VALUES (?, ?)
            """, (nome, preco))

            conn.commit()

        except sqlite3.IntegrityError:
            conn.close()
            return "Produto já cadastrado"
        

    lista = conn.execute("""
        SELECT * FROM produtos ORDER BY nome
    """).fetchall()

    conn.close()

    return render_template(
        "produtos.html",
        produtos=lista
    )

@app.route("/editar_produto/<int:id>", methods=["GET", "POST"])
@login_required
def editar_produto(id):

    conn = conectar()

    produto = conn.execute("""
        SELECT * FROM produtos WHERE id = ?
    """, (id,)).fetchone()

    if not produto:
        conn.close()
        return "Produto não encontrado."

    if request.method == "POST":

        nome = request.form["nome"].upper()
        preco = float(request.form["preco"])
        hoje = date.today()

        conn.execute("""
        UPDATE produto_precos
        SET data_fim = ?
        WHERE produto_id = ?
        AND data_fim IS NULL
        """, (hoje, id))

        # 2. CRIA NOVO PREÇO
        conn.execute("""
        INSERT INTO produto_precos
        (produto_id, preco, data_inicio)
        VALUES (?, ?, ?)
        """, (id, preco, hoje))

        # 3. (OPCIONAL) ATUALIZA PREÇO ATUAL PARA EXIBIÇÃO
        conn.execute("""
        UPDATE produtos
        SET preco = ?
        WHERE id = ?
        """, (preco, id))

        conn.commit()
        conn.close()

        return redirect(url_for("produtos"))

    conn.close()

    return render_template(
        "editar_produto.html",
        produto=produto
    )

@app.route("/excluir_produto/<int:id>")
@login_required
def excluir_produto(id):

    conn = conectar()

    # Verifica se existe movimentação
    movimentacao = conn.execute("""
        SELECT COUNT(*) as total
        FROM estoque_movimentacoes
        WHERE produto_id = ?
    """, (id,)).fetchone()["total"]

    if movimentacao > 0:
        conn.close()
        return "Não é possível excluir produto com movimentação registrada."

    conn.execute("DELETE FROM produtos WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("produtos"))

# -----------------------------
# EDITAR USUÁRIO
# -----------------------------
@app.route("/editar_usuario/<int:id>", methods=["GET","POST"])
@login_required
def editar_usuario(id):

    conn = conectar()

    if request.method == "POST":

        nome = request.form["nome"]
        usuario = request.form["usuario"]
        celular = request.form["celular"]
        cep = request.form["cep"]
        endereco = request.form["endereco"]
        numero = request.form["numero"]
        bairro = request.form["bairro"]
        senha = request.form["senha"]
        nivel = request.form["nivel"]

        conn.execute("""
        UPDATE usuarios
        SET nome=?, usuario=?, celular=?, cep=?, endereco=?, numero=?, bairro=?, senha=?, nivel=?
        WHERE id=?
        """,(nome,usuario,celular,cep,endereco,numero,bairro,senha,nivel,id))

        conn.commit()

        return redirect(url_for("usuarios"))

    usuario = conn.execute(
        "SELECT * FROM usuarios WHERE id=?",(id,)
    ).fetchone()

    conn.close()

    return render_template("editar_usuario.html", usuario=usuario)

# -----------------------------
# EXCLUIR USUÁRIO
# -----------------------------
@app.route("/excluir_usuario/<int:id>")
@login_required
@nivel_requerido(1)
def excluir_usuario(id):

    conn = conectar()

    # Não pode excluir a si mesmo
    if id == session.get("usuario_id"):
        conn.close()
        return "Você não pode excluir seu próprio usuário."

    # Verifica se é admin
    usuario = conn.execute(
        "SELECT * FROM usuarios WHERE id = ?",
        (id,)
    ).fetchone()

    if usuario["nivel"] == 1:
        # Conta quantos admins existem
        total_admins = conn.execute("""
            SELECT COUNT(*) as total
            FROM usuarios
            WHERE nivel = 1
        """).fetchone()["total"]

        if total_admins <= 1:
            conn.close()
            return "Não é possível excluir o último administrador."

    conn.execute("DELETE FROM usuarios WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("usuarios"))

@app.route("/insumos", methods=["GET","POST"])
@login_required
def insumos():

    conn = conectar()

    if request.method == "POST":

        nome = request.form["nome"].upper()
        unidade = request.form["unidade"]

        conn.execute("""
        INSERT INTO insumos (nome, unidade)
        VALUES (?,?)
        """,(nome,unidade))

        conn.commit()

    lista = conn.execute("""
    SELECT *,
    (estoque * custo_medio) AS valor_total
    FROM insumos
    ORDER BY nome
    """).fetchall()

    abc_labels = []
    abc_valores = []

    for i in lista:
        abc_labels.append(i["nome"])
        abc_valores.append(i["valor_total"])

    conn.close()

    return render_template(
        "insumos.html",
        insumos=lista,
        abc_labels=abc_labels,
        abc_valores=abc_valores
    )
@app.route("/compras", methods=["GET","POST"])
@login_required
def compras():

    conn = conectar()

    if request.method == "POST":

        insumo_id = request.form["insumo_id"]
        quantidade = float(request.form["quantidade"])
        valor_unitario = float(request.form["valor_unitario"])

        valor_total = quantidade * valor_unitario

        conn.execute("""
        INSERT INTO compras_insumos
        (insumo_id,quantidade,valor_unitario,valor_total)
        VALUES (?,?,?,?)
        """,(insumo_id,quantidade,valor_unitario,valor_total))


        insumo = conn.execute("""
        SELECT estoque,custo_medio
        FROM insumos
        WHERE id=?
        """,(insumo_id,)).fetchone()

        estoque_atual = insumo["estoque"]
        custo_atual = insumo["custo_medio"]

        novo_estoque = estoque_atual + quantidade

        novo_custo = (
            (estoque_atual * custo_atual) +
            (quantidade * valor_unitario)
        ) / novo_estoque


        conn.execute("""
        UPDATE insumos
        SET estoque=?,custo_medio=?
        WHERE id=?
        """,(novo_estoque,novo_custo,insumo_id))


        conn.commit()

    insumos = conn.execute("SELECT * FROM insumos ORDER BY nome").fetchall()

    historico = conn.execute("""
    SELECT ci.*,i.nome
    FROM compras_insumos ci
    JOIN insumos i ON i.id=ci.insumo_id
    ORDER BY ci.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "compras.html",
        insumos=insumos,
        historico=historico
    )

# -----------------------------
# VENDAS
# -----------------------------
@app.route("/vendas", methods=["GET", "POST"])
@login_required
def vendas():

    conn = conectar()

    if request.method == "POST":

        cliente_id = request.form["cliente_id"]
        data_venda = request.form["data_venda"].replace("T"," ")

        produtos_ids = request.form.getlist("produto_id")
        quantidades = request.form.getlist("quantidade")
        descontos = request.form.getlist("desconto_item[]")
        acrescimos = request.form.getlist("acrescimo_item[]")

        desconto_total = float(request.form.get("desconto_total") or 0)
        acrescimo_total = float(request.form.get("acrescimo_total") or 0)

        # =============================
        # CRIAR VENDA
        # =============================
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO vendas (cliente_id, data)
            VALUES (?, ?)
        """, (cliente_id, data_venda))

        venda_id = cursor.lastrowid

        valor_total = 0

        # =============================
        # INSERIR ITENS
        # =============================
        for i in range(len(produtos_ids)):

            produto_id = produtos_ids[i]
            quantidade = int(quantidades[i])

            desconto_item = float(descontos[i] or 0) if i < len(descontos) else 0
            acrescimo_item = float(acrescimos[i] or 0) if i < len(acrescimos) else 0

            produto = conn.execute("""
            SELECT pp.preco
            FROM produto_precos pp
            WHERE pp.produto_id = ?
            AND date('now') BETWEEN pp.data_inicio 
            AND IFNULL(pp.data_fim, date('now'))
            """, (produto_id,)).fetchone()

            custo_produto = conn.execute("""
            SELECT SUM(pi.quantidade * i.custo_medio)
            FROM produto_insumos pi
            JOIN insumos i ON i.id = pi.insumo_id
            WHERE pi.produto_id = ?
            """, (produto_id,)).fetchone()[0] or 0

            valor_unitario = produto["preco"]

            subtotal = (valor_unitario * quantidade) + acrescimo_item - desconto_item

            valor_total += subtotal

            # ✅ SALVAR ITEM CORRETAMENTE
            cursor.execute("""
            INSERT INTO venda_itens
            (venda_id, produto_id, quantidade, valor_unitario, desconto, acrescimo, custo_unitario)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                venda_id,
                produto_id,
                quantidade,
                valor_unitario,
                desconto_item,
                acrescimo_item,
                custo_produto
            ))

            item_id = cursor.lastrowid

            # =============================
            # AJUSTES POR ITEM
            # =============================
            if desconto_item > 0:
                conn.execute("""
                    INSERT INTO venda_ajustes
                    (venda_id, tipo, item_id, descricao, valor)
                    VALUES (?, 'ITEM', ?, 'Desconto', ?)
                """, (venda_id, item_id, -desconto_item))

            if acrescimo_item > 0:
                conn.execute("""
                    INSERT INTO venda_ajustes
                    (venda_id, tipo, item_id, descricao, valor)
                    VALUES (?, 'ITEM', ?, 'Acréscimo', ?)
                """, (venda_id, item_id, acrescimo_item))

            # ✅ ESTOQUE CORRETO
            conn.execute("""
                INSERT INTO estoque_movimentacoes
                (produto_id, tipo, quantidade)
                VALUES (?, 'SAIDA', ?)
            """, (produto_id, quantidade))

        # =============================
        # AJUSTES GERAIS
        # =============================
        valor_total = valor_total + acrescimo_total - desconto_total

        if desconto_total > 0:
            conn.execute("""
                INSERT INTO venda_ajustes
                (venda_id, tipo, descricao, valor)
                VALUES (?, 'TOTAL', 'Desconto Geral', ?)
            """, (venda_id, -desconto_total))

        if acrescimo_total > 0:
            conn.execute("""
                INSERT INTO venda_ajustes
                (venda_id, tipo, descricao, valor)
                VALUES (?, 'TOTAL', 'Acréscimo Geral', ?)
            """, (venda_id, acrescimo_total))

        # =============================
        # ATUALIZAR TOTAL
        # =============================
        conn.execute("""
            UPDATE vendas
            SET valor_total = ?
            WHERE id = ?
        """, (valor_total, venda_id))

        conn.commit()

    # =========================
    # LISTAGEM DE VENDAS
    # =========================
    lista_vendas = conn.execute("""
        SELECT v.id, c.nome as cliente_nome,
               v.valor_total, v.data
        FROM vendas v
        JOIN clientes c ON c.id = v.cliente_id
        ORDER BY v.data DESC
    """).fetchall()

    clientes = conn.execute("SELECT * FROM clientes").fetchall()
    produtos = conn.execute("SELECT * FROM produtos").fetchall()

    conn.close()

    return render_template(
        "vendas.html",
        clientes=clientes,
        produtos=produtos,
        vendas=lista_vendas
    )

# -----------------------------
# EXCLUIR VENDA
# -----------------------------
@app.route("/excluir_venda/<int:venda_id>")
@login_required
def excluir_venda(venda_id):

    conn = conectar()

    # Buscar itens da venda
    itens = conn.execute("""
        SELECT produto_id, quantidade
        FROM venda_itens
        WHERE venda_id = ?
    """, (venda_id,)).fetchall()

    # Devolver estoque
    for item in itens:

        conn.execute("""
            INSERT INTO estoque_movimentacoes
            (produto_id, tipo, quantidade)
            VALUES (?, 'ENTRADA', ?)
        """, (item["produto_id"], item["quantidade"]))

    # Excluir itens da venda
    conn.execute("""
        DELETE FROM venda_itens
        WHERE venda_id = ?
    """, (venda_id,))

    # Excluir venda
    conn.execute("""
        DELETE FROM vendas
        WHERE id = ?
    """, (venda_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("vendas"))

@app.route("/precificacao", methods=["GET","POST"])
@login_required
def precificacao():

    conn = conectar()

    produto_id = request.args.get("produto")

    if request.method == "POST":

        produto_id = request.form["produto_id"]
        insumos = request.form.getlist("insumo_id")
        quantidades = request.form.getlist("quantidade")

        conn.execute("""
        DELETE FROM produto_insumos
        WHERE produto_id = ?
        """,(produto_id,))

        for i in range(len(insumos)):

            conn.execute("""

            INSERT INTO produto_insumos
            (produto_id,insumo_id,quantidade)

            VALUES (?,?,?)

            """,(produto_id,insumos[i],quantidades[i]))

        conn.commit()
        return redirect(url_for("precificacao", produto=produto_id))

    produtos = conn.execute("""
    SELECT * FROM produtos ORDER BY nome
    """).fetchall()

    insumos = conn.execute("""
    SELECT * FROM insumos ORDER BY nome
    """).fetchall()

    ficha = []
    custo_total = 0

    if produto_id:

        ficha = conn.execute("""

        SELECT 
        pi.id,
        pi.insumo_id,
        pi.quantidade,
        i.nome,
        i.unidade,
        i.custo_medio,
        (pi.quantidade * i.custo_medio) as custo

        FROM produto_insumos pi
        JOIN insumos i ON i.id = pi.insumo_id

        WHERE pi.produto_id = ?

        """,(produto_id,)).fetchall()

        custo_total = sum(f["custo"] for f in ficha)

    conn.close()

    return render_template(
        "precificacao.html",
        produtos=produtos,
        insumos=insumos,
        ficha=ficha,
        produto_id=produto_id,
        custo_total=custo_total
    )
# -----------------------------
# DETALHE DA VENDA
# -----------------------------
@app.route("/detalhe_venda/<int:id>")
@login_required
def detalhe_venda(id):

    conn = conectar()

    # Buscar venda
    venda = conn.execute("""
        SELECT v.id, v.data, v.valor_total,
               c.nome as cliente_nome
        FROM vendas v
        JOIN clientes c ON c.id = v.cliente_id
        WHERE v.id = ?
    """, (id,)).fetchone()

    ajustes = conn.execute("""
    SELECT * FROM venda_ajustes
    WHERE venda_id = ?
    """, (id,)).fetchall()

    if not venda:
        conn.close()
        return "Venda não encontrada", 404

    # Buscar itens da venda
    itens = conn.execute("""
        SELECT p.nome,
            vi.quantidade,
            vi.valor_unitario,
            vi.desconto,
            vi.acrescimo,
            (vi.quantidade * vi.valor_unitario + vi.acrescimo - vi.desconto) as subtotal
        FROM venda_itens vi
        JOIN produtos p ON p.id = vi.produto_id
        WHERE vi.venda_id = ?
    """, (id,)).fetchall()

    conn.close()

    return render_template(
    "detalhe_venda.html",
    venda=venda,
    itens=itens,
    ajustes=ajustes
    )


@app.route("/empresa", methods=["GET", "POST"])
@login_required
@nivel_requerido(1)
def empresa():

    conn = conectar()

    if request.method == "POST":
        nome = request.form["nome"]
        mensagem = request.form["mensagem"]

        logo = request.files["logo"]
        logo_path = None

        if logo:
            logo_filename = secure_filename(logo.filename)
            save_path = os.path.join("static", "uploads", logo_filename)

            logo.save(save_path)

            logo_path = f"uploads/{logo_filename}"  # salvar relativo no banco

        empresa_existente = conn.execute("SELECT * FROM empresa").fetchone()

        if empresa_existente:
            conn.execute("""
                UPDATE empresa
                SET nome=?, logo=?, mensagem_rodape=?
                WHERE id=?
            """, (nome, logo_path, mensagem, empresa_existente["id"]))
        else:
            conn.execute("""
                INSERT INTO empresa (nome, logo, mensagem_rodape)
                VALUES (?, ?, ?)
            """, (nome, logo_path, mensagem))

        conn.commit()

    empresa = conn.execute("SELECT * FROM empresa LIMIT 1").fetchone()
    conn.close()

    return render_template("empresa.html", empresa=empresa)

# ---------------------------------
# CONTAS FIXAS
# ---------------------------------

@app.route("/contas_fixas", methods=["GET","POST"])
@login_required
def contas_fixas():

    conn = conectar()

    if request.method == "POST":

        descricao = request.form["descricao"]
        valor = float(request.form["valor"])
        data_vencimento = request.form["data_vencimento"]

        conn.execute("""
        INSERT INTO contas_fixas
        (descricao,valor,data_vencimento)
        VALUES (?,?,?)
        """,(descricao,valor,data_vencimento))

        conn.commit()

    contas = conn.execute("""
    SELECT * FROM contas_fixas
    ORDER BY data_vencimento
    """).fetchall()

    conn.close()

    return render_template(
        "contas_fixas.html",
        contas=contas
    )

# ---------------------------------
# EDITAR CONTA
# ---------------------------------

@app.route("/editar_conta/<int:id>", methods=["GET","POST"])
@login_required
def editar_conta(id):

    conn = conectar()

    if request.method == "POST":

        descricao = request.form["descricao"]
        valor = float(request.form["valor"])
        data = request.form["data_vencimento"]

        conn.execute("""
        UPDATE contas_fixas
        SET descricao=?, valor=?, data_vencimento=?
        WHERE id=?
        """,(descricao,valor,data,id))

        conn.commit()
        conn.close()

        return redirect(url_for("contas_fixas"))

    conta = conn.execute("""
    SELECT * FROM contas_fixas WHERE id=?
    """,(id,)).fetchone()

    conn.close()

    return render_template(
        "editar_conta.html",
        conta=conta
    )

# ---------------------------------
# EXCLUIR CONTA
# ---------------------------------

@app.route("/excluir_conta/<int:id>")
@login_required
def excluir_conta(id):

    conn = conectar()

    conn.execute("""
    DELETE FROM contas_fixas
    WHERE id=?
    """,(id,))

    conn.commit()
    conn.close()

    return redirect(url_for("contas_fixas"))

# -----------------------------
# DRE - FINANCEIRO
# -----------------------------

@app.route("/dre")
@login_required
def dre():

    conn = conectar()

    # ================= RECEITA =================

    receita = conn.execute("""
    SELECT IFNULL(SUM(
        (vi.quantidade * vi.valor_unitario)
        + vi.acrescimo
        - vi.desconto
    ),0)
    FROM venda_itens vi
    """).fetchone()[0]


    # ================= CMV =================

    cmv = conn.execute("""
    SELECT IFNULL(SUM(
        vi.quantidade * vi.custo_unitario
    ),0)
    FROM venda_itens vi
    """).fetchone()[0]


    # ================= CUSTOS FIXOS =================

    custos_fixos = conn.execute("""
    SELECT IFNULL(SUM(valor),0)
    FROM contas_fixas
    """).fetchone()[0]

    # ------------------- ÇUCRATIVIDADE --------------

    rows = conn.execute("""
    SELECT 
        p.nome,

        SUM(vi.quantidade) as total_vendido,

        SUM(
            (vi.quantidade * vi.valor_unitario)
            + COALESCE(vi.acrescimo,0)
            - COALESCE(vi.desconto,0)
        ) as receita,

        SUM(
            vi.quantidade * vi.custo_unitario
        ) as custo,

        SUM(
            (vi.quantidade * vi.valor_unitario)
            + COALESCE(vi.acrescimo,0)
            - COALESCE(vi.desconto,0)
            - (vi.quantidade * vi.custo_unitario)
        ) as lucro

    FROM venda_itens vi
    JOIN produtos p ON p.id = vi.produto_id

    GROUP BY p.nome
    ORDER BY lucro DESC
    """).fetchall()
    produtos_lucratividade = [dict(r) for r in rows]

    # ================= RESULTADOS =================

    lucro_bruto = receita - cmv
    lucro_liquido = lucro_bruto - custos_fixos
    
    margem_contrib = 0

    if receita > 0:
        margem_contrib = (lucro_bruto / receita) * 100


    ponto_equilibrio = 0

    if margem_contrib > 0:
        ponto_equilibrio = custos_fixos / (margem_contrib / 100)

    cmv_por_mes = conn.execute("""
    SELECT 
        strftime('%Y-%m', v.data) as mes,
        IFNULL(SUM(
            vi.quantidade * vi.custo_unitario
        ),0) as cmv
    FROM venda_itens vi
    JOIN vendas v ON v.id = vi.venda_id
    GROUP BY mes
    ORDER BY mes
    """).fetchall()

    # ================= DADOS DO GRÁFICO =================

    vendas_mes = conn.execute("""

    SELECT
    strftime('%Y-%m', v.data) as mes,
    SUM(v.valor_total) as receita

    FROM vendas v

    GROUP BY mes
    ORDER BY mes

    """).fetchall()


    labels = []
    receita_mensal = []
    cmv_mensal = []
    lucro_mensal = []
    produtos_prejuizo = [p for p in produtos_lucratividade if p["lucro"] < 0]
    # criar dicionário de CMV por mês
    cmv_dict = {c["mes"]: c["cmv"] for c in cmv_por_mes}

    for v in vendas_mes:

        mes = v["mes"]
        receita_mes = v["receita"]
        cmv_mes = cmv_dict.get(mes, 0)

        labels.append(mes)
        receita_mensal.append(receita_mes)
        cmv_mensal.append(cmv_mes)
        lucro_mensal.append(receita_mes - cmv_mes)
    
    for p in produtos_lucratividade:
        receita_produto = p["receita"] or 0
        lucro_produto = p["lucro"] or 0

        if receita_produto > 0:
            p["margem"] = (lucro_produto / receita_produto) * 100
        else:
            p["margem"] = 0
    top_produtos = produtos_lucratividade[:5]

    conn.close()

    return render_template(
    "dre.html",

    # já existentes
    receita=receita,
    cmv=cmv,
    custos_fixos=custos_fixos,
    lucro_bruto=lucro_bruto,
    lucro_liquido=lucro_liquido,
    margem_contrib=margem_contrib,
    ponto_equilibrio=ponto_equilibrio,

    labels=labels,
    receita_mensal=receita_mensal,
    cmv_mensal=cmv_mensal,
    lucro_mensal=lucro_mensal,

    # NOVO
    top_produtos=top_produtos,
    produtos_prejuizo=produtos_prejuizo,
    produtos_lucratividade=produtos_lucratividade
    )

# -----------------------------
# EMITIR COMPROVANTE
# -----------------------------
@app.route("/emitir_comprovante/<int:venda_id>", methods=["GET", "POST"])
@login_required
def emitir_comprovante(venda_id):

    conn = conectar()

    venda = conn.execute("""
        SELECT v.id, v.data, v.valor_total,
               c.nome as cliente_nome
        FROM vendas v
        JOIN clientes c ON c.id = v.cliente_id
        WHERE v.id = ?
    """, (venda_id,)).fetchone()

    itens = conn.execute("""
        SELECT p.nome,
            vi.quantidade,
            vi.valor_unitario,
            IFNULL(vi.desconto,0) as desconto,
            IFNULL(vi.acrescimo,0) as acrescimo,
            (
                (vi.quantidade * vi.valor_unitario)
                + IFNULL(vi.acrescimo,0)
                - IFNULL(vi.desconto,0)
            ) as subtotal
        FROM venda_itens vi
        JOIN produtos p ON p.id = vi.produto_id
        WHERE vi.venda_id = ?
    """, (venda_id,)).fetchall()

    ajustes = conn.execute("""
    SELECT IFNULL(SUM(valor),0)
    FROM venda_ajustes
    WHERE venda_id = ?
    """,(venda_id,)).fetchone()[0]

    empresa = conn.execute("SELECT * FROM empresa LIMIT 1").fetchone()

    conn.close()

    if request.method == "POST":

        tipo = request.form["tipo"]
        pagamento = request.form["pagamento"]
        observacao = request.form["observacao"]
        formato = request.form["formato"]
        valor_extra = float(request.form.get("valor_extra") or 0)

        # corrigir quebra de linha
        if observacao:
            observacao = observacao.replace("\n", "<br/>")

        total_final = venda["valor_total"] + valor_extra

        buffer = BytesIO()

        # ====================================================
        # CUPOM TÉRMICO
        # ====================================================
        if formato == "CUPOM":

            largura = 80 * mm
            altura = 300 * mm

            doc = SimpleDocTemplate(
                buffer,
                pagesize=(largura, altura),
                leftMargin=5,
                rightMargin=5,
                topMargin=5,
                bottomMargin=5
            )

            elements = []

            center = ParagraphStyle(
                name="center",
                alignment=TA_CENTER,
                fontSize=10
            )

            normal = ParagraphStyle(
                name="normal",
                fontSize=9
            )

            # LOGO
            if empresa and empresa["logo"]:
                logo_path = empresa["logo"]
                if os.path.exists(logo_path):
                    img = Image(logo_path, width=50*mm)
                    img.hAlign = "CENTER"
                    elements.append(img)

            # NOME EMPRESA
            if empresa:
                elements.append(Paragraph(f"<b>{empresa['nome']}</b>", center))

            elements.append(Spacer(1,5))

            elements.append(Paragraph(f"Cliente: {venda['cliente_nome']}", normal))
            elements.append(Paragraph(f"Data: {venda['data']}", normal))
            elements.append(Paragraph(f"Pagamento: {pagamento}", normal))
            elements.append(Paragraph(f"Tipo: {tipo}", normal))

            elements.append(Spacer(1,5))
            elements.append(Paragraph("------------------------------------------", center))

            total_itens = 0

            for item in itens:

                linha = f"""
                {item['nome']}<br/>
                {item['quantidade']} x {item['valor_unitario']:.2f}
                """

                if item["desconto"] > 0:
                    linha += f"<br/>Desconto: -R$ {item['desconto']:.2f}"

                if item["acrescimo"] > 0:
                    linha += f"<br/>Acréscimo: +R$ {item['acrescimo']:.2f}"

                linha += f"<br/>Subtotal: R$ {item['subtotal']:.2f}"

                elements.append(Paragraph(linha, normal))

                total_itens += item["quantidade"]

            elements.append(Paragraph("------------------------------------------", center))

            elements.append(Paragraph(f"Total de itens: {total_itens}", normal))
            elements.append(Paragraph(f"<b>TOTAL: R$ {total_final:.2f}</b>", center))

            if observacao:
                elements.append(Spacer(1,5))
                elements.append(Paragraph("Observação:", normal))
                elements.append(Spacer(1,3))
                elements.append(Paragraph(observacao, normal))

            elements.append(Spacer(1,10))

            if empresa and empresa["mensagem_rodape"]:

                rodape = empresa["mensagem_rodape"]

                if rodape:
                    rodape = rodape.replace("\n", "<br/>")
                    elements.append(Spacer(1,10))
                    elements.append(Paragraph(rodape, center))

            doc.build(elements)

        # ====================================================
        # COMPROVANTE A4
        # ====================================================
        else:

            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                leftMargin=30,
                rightMargin=30,
                topMargin=30,
                bottomMargin=30
            )

            elements = []
            styles = getSampleStyleSheet()

            center = ParagraphStyle(
                name="center",
                alignment=TA_CENTER,
                fontSize=12
            )

            normal = ParagraphStyle(
                name="normal",
                fontSize=10
            )

            # LOGO
            if empresa and empresa["logo"]:
                logo_path = empresa["logo"]
                if os.path.exists(logo_path):
                    img = Image(logo_path, width=80*mm)
                    img.hAlign = "CENTER"
                    elements.append(img)

            if empresa:
                elements.append(
                    Paragraph(f"<b>{empresa['nome']}</b>", center)
                )

            elements.append(Spacer(1,15))

            elements.append(Paragraph(f"<b>Cliente:</b> {venda['cliente_nome']}", normal))
            elements.append(Paragraph(f"<b>Data:</b> {venda['data']}", normal))
            elements.append(Paragraph(f"<b>Pagamento:</b> {pagamento}", normal))
            elements.append(Paragraph(f"<b>Tipo:</b> {tipo}", normal))

            elements.append(Spacer(1,15))

            data = [
                ["Produto", "Qtd", "Unit", "Desc", "Acrésc", "Subtotal"]
                ]

            produto_style = ParagraphStyle(
                "produto",
                fontSize=9,
                leading=11
            )

            data = [
            [
            Paragraph("<b>Produto</b>", produto_style),
            Paragraph("<b>Qtd</b>", produto_style),
            Paragraph("<b>Valor Unit.</b>", produto_style),
            Paragraph("<b>Desc.</b>", produto_style),
            Paragraph("<b>Acrésc.</b>", produto_style),
            Paragraph("<b>Subtotal</b>", produto_style)
            ]
            ]

            for item in itens:

                data.append([
                    Paragraph(item["nome"], produto_style),
                    Paragraph(str(item["quantidade"]), produto_style),
                    Paragraph(f"R$ {item['valor_unitario']:.2f}", produto_style),
                    Paragraph(
                        f"<font color='red'>-R$ {item['desconto']:.2f}</font>",
                        produto_style
                    ),
                    Paragraph(
                        f"<font color='green'>+R$ {item['acrescimo']:.2f}</font>",
                        produto_style
                    ),
                    Paragraph(f"R$ {item['subtotal']:.2f}", produto_style)
                ])

            table = Table(
            data,
            colWidths=[180,40,80,80,80,100],
            repeatRows=1
            )

            table.setStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
            ("GRID",(0,0),(-1,-1),1,colors.black),

            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),

            ("ALIGN",(1,1),(3,-1),"CENTER"),
            ])

            elements.append(table)

            elements.append(Spacer(1,20))

            if valor_extra > 0:
                elements.append(
                    Paragraph(f"<b>Valor adicional:</b> R$ {valor_extra:.2f}", normal)
                )

            elements.append(
                Paragraph(f"<b>Total da Venda: R$ {total_final:.2f}</b>", styles["Heading2"])
            )

            if observacao:
                elements.append(Spacer(1,10))
                elements.append(Paragraph("<b>Observação:</b>", normal))
                elements.append(Paragraph(observacao, normal))

            if empresa and empresa["mensagem_rodape"]:

                rodape = empresa["mensagem_rodape"]

                if rodape:
                    rodape = rodape.replace("\n", "<br/>")
                    elements.append(Spacer(1,10))
                    elements.append(Paragraph(rodape, center))

            doc.build(elements)

        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"Comprovante_Venda_{venda_id}.pdf",
            mimetype="application/pdf"
        )

    return render_template(
        "emitir_comprovante.html",
        venda=venda,
        itens=itens
    )

UPLOAD_FOLDER = "static/uploads"

@app.route("/cadastro", methods=["GET","POST"])
def cadastro_usuario():

    if request.method == "POST":

        conn = conectar()

        nome = request.form["nome"].upper().strip()
        usuario = request.form["usuario"].upper().strip()
        senha = request.form["senha"]

        celular = request.form.get("celular")
        cep = request.form.get("cep")
        endereco = request.form.get("endereco")
        numero = request.form.get("numero")
        bairro = request.form.get("bairro")

        nivel = 5

        # verifica se login já existe
        existe = conn.execute("""
        SELECT id FROM usuarios WHERE usuario = ?
        """,(usuario,)).fetchone()

        if existe:
            conn.close()
            return "Este login já está em uso."

        # cria usuário
        conn.execute("""
        INSERT INTO usuarios
        (nome, usuario, senha, celular, cep, endereco, numero, bairro, nivel)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,(nome,usuario,senha,celular,cep,endereco,numero,bairro,nivel))

        # verifica se cliente já existe pelo telefone
        cliente = conn.execute("""
        SELECT id FROM clientes WHERE telefone = ?
        """,(celular,)).fetchone()

        if not cliente:

            conn.execute("""
            INSERT INTO clientes
            (nome, telefone, documento, endereco)
            VALUES (?,?,?,?)
            """,(
                nome,
                celular,
                None,
                endereco
            ))

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("cadastro.html")


# LOJA ONLINE -------------------------------
@app.route("/loja")
def loja():

    conn = conectar()

    categoria = request.args.get("categoria")
    carrinho = session.get("carrinho", [])
    total_itens = sum(item["quantidade"] for item in carrinho)

    categorias = conn.execute("""
    SELECT DISTINCT categoria
    FROM produtos_leadpage
    WHERE ativo = 1
    ORDER BY categoria
    """).fetchall()

    if categoria:

        produtos = conn.execute("""
        SELECT * FROM produtos_leadpage
        WHERE ativo = 1 AND categoria = ?
        ORDER BY nome
        """,(categoria,)).fetchall()

    else:

        produtos = conn.execute("""
        SELECT * FROM produtos_leadpage
        WHERE ativo = 1
        ORDER BY categoria,nome
        """).fetchall()

    conn.close()

    return render_template(
        "loja.html",
        produtos=produtos,
        categorias=categorias,
        categoria_atual=categoria,
        total_itens=total_itens
    )

# CARRINHO -------------------------------
@app.route("/adicionar_carrinho/<int:id>")
@login_required
def adicionar_carrinho(id):

    conn = conectar()

    produto = conn.execute("""
    SELECT * FROM produtos_leadpage
    WHERE id=?
    """,(id,)).fetchone()

    conn.close()

    carrinho = session.get("carrinho", [])

    carrinho.append({
        "id": produto["id"],
        "nome": produto["nome"],
        "preco": produto["preco"],
        "quantidade": 1
    })

    session["carrinho"] = carrinho

    return redirect(url_for("loja"))

@app.route("/carrinho_quantidade")
@login_required
def carrinho_quantidade():

    carrinho = session.get("carrinho", [])

    total = sum(item["quantidade"] for item in carrinho)

    return {"total": total}

# TELA CARRINHO -------------------------------
@app.route("/carrinho")
@login_required
def carrinho():

    carrinho = session.get("carrinho", [])

    total = sum(i["preco"] * i["quantidade"] for i in carrinho)

    return render_template(
        "carrinho.html",
        carrinho=carrinho,
        total=total
    )

@app.route("/remover_carrinho/<int:index>")
@login_required
def remover_carrinho(index):

    carrinho = session.get("carrinho", [])

    if 0 <= index < len(carrinho):
        carrinho.pop(index)

    session["carrinho"] = carrinho

    return redirect(url_for("carrinho"))


@app.route("/finalizar_pedido", methods=["POST"])
@login_required
def finalizar_pedido():

    conn = conectar()

    carrinho = session.get("carrinho", [])

    observacoes = request.form["observacoes"]
    data_agendamento = request.form.get("data_agendamento")
    hora_agendamento = request.form.get("hora_agendamento")
    tipo_entrega = request.form.get("tipo_entrega")

    usuario = conn.execute("""
    SELECT * FROM usuarios WHERE id=?
    """,(session["usuario_id"],)).fetchone()

    valor_produtos = sum(i["preco"] * i["quantidade"] for i in carrinho)

    valor_entrega = 0

    valor_total = valor_produtos + valor_entrega
    
    cur = conn.cursor()

    cur.execute("""
    SELECT COUNT(*)
    FROM pedidos_online
    WHERE data_agendamento = ?
    """,(data_agendamento,))

    total_dia = cur.fetchone()[0]

    if total_dia >= 5:

        flash("Agenda cheia para este dia. Entraremos em contato para confirmar disponibilidade.")

    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO pedidos_online
    (
    usuario_id,
    nome_cliente,
    telefone,
    endereco,
    valor_produtos,
    valor_entrega,
    valor_total,
    observacoes,
    data_agendamento,
    hora_agendamento,
    tipo_entrega
    )
    VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """,
    (
    usuario["id"],
    usuario["nome"],
    usuario["celular"],
    usuario["endereco"],
    valor_produtos,
    valor_entrega,
    valor_total,
    observacoes,
    data_agendamento,
    hora_agendamento,
    tipo_entrega
    ))

    pedido_id = cursor.lastrowid

    for item in carrinho:

        conn.execute("""
        INSERT INTO pedido_itens
        (pedido_id,produto_id,nome_produto,quantidade,valor)
        VALUES (?,?,?,?,?)
        """,
        (
        pedido_id,
        item["id"],
        item["nome"],
        item["quantidade"],
        item["preco"]
        ))

    conn.commit()
    conn.close()

    session["carrinho"] = []

    # mensagem de sucesso
    flash("Pedido enviado com sucesso!")

    flash("pedido_sucesso")
    return redirect(url_for("carrinho"))

#administrador de pedidos-------------------
@app.route("/admin/pedidos")
@login_required
@nivel_requerido(1)
def pedidos_online():

    conn = conectar()

    pedidos_db = conn.execute("""
        SELECT *
        FROM pedidos_online
        ORDER BY data DESC
    """).fetchall()

    pedidos = []

    for p in pedidos_db:

        pedido = dict(p)   # converte Row -> dict

        itens = conn.execute("""
            SELECT *
            FROM pedido_itens
            WHERE pedido_id = ?
        """, (p["id"],)).fetchall()

        pedido["itens"] = itens

        pedidos.append(pedido)

    conn.close()

    pedidos_novos = sum(1 for p in pedidos if p["status"] == "NOVO")

    return render_template(
        "admin_pedidos.html",
        pedidos=pedidos,
        pedidos_novos=pedidos_novos
    )

#alterar os status --------------------------------------
@app.route("/alterar_status/<int:id>/<status>")
@login_required
@nivel_requerido(1)
def alterar_status(id,status):

    conn = conectar()

    conn.execute("""
    UPDATE pedidos_online
    SET status=?
    WHERE id=?
    """,(status,id))

    conn.commit()
    conn.close()

    return redirect(url_for("pedidos_online"))

# MEUS PEDIDOS E ACOMPANHAMENTO --------------------
@app.route("/meus_pedidos")
@login_required
def meus_pedidos():

    conn = conectar()

    pedidos = conn.execute("""
    SELECT *
    FROM pedidos_online
    WHERE usuario_id=?
    ORDER BY id DESC
    """,(session["usuario_id"],)).fetchall()

    pedidos_lista = []

    for p in pedidos:

        itens = conn.execute("""
        SELECT *
        FROM pedido_itens
        WHERE pedido_id=?
        """,(p["id"],)).fetchall()

        pedido = dict(p)
        pedido["itens"] = itens

        pedidos_lista.append(pedido)

    conn.close()

    return render_template(
        "meus_pedidos.html",
        pedidos=pedidos_lista
    )

@app.route("/admin/excluir_produto_loja/<int:id>")
@login_required
@nivel_requerido(1)
def excluir_produto_loja(id):

    conn = conectar()

    conn.execute("""
    DELETE FROM produtos_leadpage
    WHERE id=?
    """,(id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_produtos_loja"))

#adminsitrador de produtos --------------------------------------------
@app.route("/admin/produtos_loja")
@login_required
@nivel_requerido(1)
def admin_produtos_loja():

    conn = conectar()

    produtos = conn.execute("""
    SELECT * FROM produtos_leadpage
    ORDER BY categoria,nome
    """).fetchall()

    conn.close()

    return render_template(
        "admin_produtos_loja.html",
        produtos=produtos
    )

#salvar_produto------------------------------
@app.route("/admin/salvar_produto_loja", methods=["POST"])
@login_required
@nivel_requerido(1)
def salvar_produto_loja():

    conn = conectar()

    nome = request.form["nome"]
    categoria = request.form["categoria"]
    preco = request.form["preco"]
    descricao = request.form["descricao"]

    imagem = request.files["imagem"]

    nome_arquivo = None

    if imagem and imagem.filename != "":

        nome_arquivo = secure_filename(imagem.filename)

        pasta = os.path.join(BASE_DIR, "static", "produtos")
        os.makedirs(pasta, exist_ok=True)

        caminho = os.path.join(pasta, nome_arquivo)

        imagem.save(caminho)

    conn.execute("""

    INSERT INTO produtos_leadpage
    (nome,categoria,preco,descricao,imagem)

    VALUES (?,?,?,?,?)

    """,(nome,categoria,preco,descricao,nome_arquivo))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_produtos_loja"))

# EDITAR PRODUTO DA LEADPAGE
@app.route("/admin/editar_produto_loja/<int:id>", methods=["GET","POST"])
@login_required
@nivel_requerido(1)
def editar_produto_loja(id):

    conn = conectar()

    if request.method == "POST":

        nome = request.form["nome"]
        categoria = request.form["categoria"]
        preco = request.form["preco"]
        descricao = request.form["descricao"]

        imagem = request.files.get("imagem")

        # buscar imagem atual
        produto_atual = conn.execute("""
        SELECT imagem FROM produtos_leadpage
        WHERE id=?
        """,(id,)).fetchone()

        nome_imagem = produto_atual["imagem"]

        if imagem and imagem.filename != "":

            nome_imagem = secure_filename(imagem.filename)

            pasta = os.path.join(BASE_DIR, "static", "produtos")
            os.makedirs(pasta, exist_ok=True)

            caminho = os.path.join(pasta, nome_imagem)

            imagem.save(caminho)

        conn.execute("""
        UPDATE produtos_leadpage
        SET nome=?, categoria=?, preco=?, descricao=?, imagem=?
        WHERE id=?
        """,(nome,categoria,preco,descricao,nome_imagem,id))

        conn.commit()
        conn.close()

        return redirect(url_for("admin_produtos_loja"))

    produto = conn.execute("""
    SELECT * FROM produtos_leadpage
    WHERE id=?
    """,(id,)).fetchone()

    conn.close()

    return render_template(
        "editar_produto_loja.html",
        produto=produto
    )

@app.route("/verificar_agenda")
def verificar_agenda():

    data = request.args.get("data")
    hora = request.args.get("hora")

    conn = conectar()
    cur = conn.cursor()

    # buscar configuração do calendário
    cur.execute("""
        SELECT disponivel, limite_encomendas, limite_por_hora
        FROM calendario_disponibilidade
        WHERE data = ?
    """, (data,))

    config = cur.fetchone()

    # se não houver configuração assume padrão
    if not config:

        limite_dia = 5
        limite_hora = 2
        disponivel = 1

    else:

        disponivel = config[0]
        limite_dia = config[1]
        limite_hora = config[2]

    # dia bloqueado
    if disponivel == 0:

        conn.close()

        return {
            "ocupado": True,
            "motivo": "dia_bloqueado"
        }

    # contar pedidos no dia
    cur.execute("""
        SELECT COUNT(*)
        FROM pedidos_online
        WHERE data_agendamento = ?
        AND status != 'RECUSADO'
    """, (data,))

    total_dia = cur.fetchone()[0]

    # contar pedidos no horário
    cur.execute("""
        SELECT COUNT(*)
        FROM pedidos_online
        WHERE data_agendamento = ?
        AND hora_agendamento = ?
        AND status != 'RECUSADO'
    """, (data, hora))

    total_hora = cur.fetchone()[0]

    conn.close()

    ocupado = False

    if total_dia >= limite_dia:
        ocupado = True

    if total_hora >= limite_hora:
        ocupado = True

    return {
        "ocupado": ocupado,
        "total_dia": total_dia,
        "total_hora": total_hora
    }

@app.route("/agenda")
def agenda_home():

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM calendario_disponibilidade
        ORDER BY data
    """)

    dias = cur.fetchall()

    conn.close()

    return render_template("agenda.html", dias=dias)


@app.route("/agenda/salvar", methods=["POST"])
def salvar_agenda():

    data = request.form["data"]
    limite = request.form["limite"]
    limite_hora = request.form["limite_hora"]
    disponivel = request.form.get("disponivel", 1)

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO calendario_disponibilidade
        (data, disponivel, limite_encomendas, limite_por_hora)
        VALUES (?, ?, ?, ?)
    """, (data, disponivel, limite, limite_hora))

    conn.commit()
    conn.close()

    return redirect(url_for("agenda_home"))


@app.route("/agenda/bloquear/<data>")
def bloquear_dia(data):

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        UPDATE calendario_disponibilidade
        SET disponivel = 0
        WHERE data = ?
    """, (data,))

    conn.commit()
    conn.close()

    return redirect(url_for("agenda_home"))


@app.route("/agenda/liberar/<data>")
def liberar_dia(data):

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        UPDATE calendario_disponibilidade
        SET disponivel = 1
        WHERE data = ?
    """, (data,))

    conn.commit()
    conn.close()

    return redirect(url_for("agenda_home"))

@app.route("/")
def home():
    if "usuario" in session:
        return redirect(url_for("loja"))

    conn = conectar()

    produtos = conn.execute("""
    SELECT * FROM produtos_leadpage
    WHERE ativo = 1
    """).fetchall()

    categorias = conn.execute("""
    SELECT DISTINCT categoria
    FROM produtos_leadpage
    WHERE ativo = 1
    ORDER BY categoria
    """).fetchall()

    promocoes = conn.execute("""
    SELECT * FROM produtos_leadpage
    WHERE ativo = 1 AND categoria = 'Promoções do dia'
    """).fetchall()

    conn.close()

    return render_template(
    "landing.html",
    produtos=produtos,
    categorias=categorias,
    promocoes=promocoes
    )
@app.route("/calcular_frete")
def calcular_frete():

    endereco_cliente = request.args.get("endereco")

    endereco_loja = "Rua da sua confeitaria, Sete Lagoas MG"

    api_key = "SUA_API_KEY"

    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={endereco_loja}&destinations={endereco_cliente}&key={api_key}"

    import requests
    response = requests.get(url).json()

    distancia_metros = response["rows"][0]["elements"][0]["distance"]["value"]

    km = distancia_metros / 1000

    taxa = 5 + (km * 2.60)

    return {"taxa": round(taxa, 2)}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
