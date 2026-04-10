import sqlite3
from config import Config

DATABASE = Config.DATABASE_PATH

def conectar():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    # =============================
    # USUÁRIOS
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        usuario TEXT UNIQUE,
        senha TEXT NOT NULL,
        celular TEXT,
        cep TEXT,
        endereco TEXT,
        numero TEXT,
        bairro TEXT,
        nivel INTEGER NOT NULL CHECK (nivel BETWEEN 0 AND 5)
    )
    """)

    # =============================
    # MIGRAÇÃO TABELA USUARIOS
    # =============================

    colunas = cursor.execute("PRAGMA table_info(usuarios)").fetchall()
    nomes_colunas = [c[1] for c in colunas]

    if "usuario" not in nomes_colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN usuario TEXT")

    if "celular" not in nomes_colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN celular TEXT")

    if "cep" not in nomes_colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN cep TEXT")

    if "endereco" not in nomes_colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN endereco TEXT")

    if "numero" not in nomes_colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN numero TEXT")

    if "bairro" not in nomes_colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN bairro TEXT")

    # =============================
    # ADMIN PADRÃO
    # =============================
    admin = cursor.execute("""
    SELECT * FROM usuarios WHERE nome = ?
    """, ("ADMIN",)).fetchone()

    if not admin:
        cursor.execute("""
        INSERT INTO usuarios (nome, senha, nivel)
        VALUES (?, ?, ?)
        """, ("ADMIN", "ADMIN", 1))

    conn.commit()

    # =============================
    # EMPRESA
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS empresa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        logo TEXT,
        mensagem_rodape TEXT
    )
    """)

    # =============================
    # CLIENTES
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        telefone TEXT,
        documento TEXT,
        endereco TEXT
    )
    """)

    # =============================
    # PRODUTOS
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        preco REAL DEFAULT 0
    )
    """)

    # =============================
    # PRODUTOS
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produto_precos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER,
    preco REAL,
    data_inicio DATE,
    data_fim DATE
    )
    """)

    # =============================
    # MOVIMENTAÇÃO ESTOQUE PRODUTOS
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque_movimentacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL,
        tipo TEXT NOT NULL CHECK(tipo IN ('ENTRADA','SAIDA')),
        quantidade INTEGER NOT NULL,
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produto_id) REFERENCES produtos(id)
    )
    """)

    # =============================
    # VENDAS
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        valor_total REAL DEFAULT 0,
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
    )
    """)

    # =============================
    # ITENS DA VENDA
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venda_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER NOT NULL,
        produto_id INTEGER NOT NULL,
        quantidade INTEGER NOT NULL,
        valor_unitario REAL NOT NULL,
        FOREIGN KEY (venda_id) REFERENCES vendas(id),
        FOREIGN KEY (produto_id) REFERENCES produtos(id)
    )
    """)
    # =============================
    # DESCONTOS DE VENDA
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venda_ajustes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER,
        tipo TEXT,
        item_id INTEGER,
        descricao TEXT,
        valor REAL
    )
    """)

    # =====================================================
    # NOVOS MÓDULOS FINANCEIROS
    # =====================================================

    # =============================
    # INSUMOS
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS insumos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        unidade TEXT,
        custo_medio REAL DEFAULT 0
    )
    """)

    # verifica se coluna existe
    colunas = cursor.execute("PRAGMA table_info(insumos)").fetchall()

    nomes_colunas = [c[1] for c in colunas]

    if "estoque" not in nomes_colunas:
        cursor.execute("""
        ALTER TABLE insumos ADD COLUMN estoque REAL DEFAULT 0
        """)

    # =============================
    # COMPRAS DE INSUMOS
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compras_insumos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        insumo_id INTEGER NOT NULL,
        quantidade REAL NOT NULL,
        valor_unitario REAL NOT NULL,
        valor_total REAL NOT NULL,
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (insumo_id) REFERENCES insumos(id)
    )
    """)

    # =============================
    # CUSTOS FIXOS
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contas_fixas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL,
        valor REAL NOT NULL,
        data_vencimento DATE NOT NULL
    )
    """)

    # =============================
    # MOVIMENTAÇÃO ESTOQUE INSUMOS
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque_insumos_mov (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        insumo_id INTEGER NOT NULL,
        tipo TEXT NOT NULL CHECK(tipo IN ('ENTRADA','SAIDA')),
        quantidade REAL NOT NULL,
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (insumo_id) REFERENCES insumos(id)
    )
    """)

    # =============================
    # FICHA TÉCNICA DO PRODUTO
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produto_insumos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL,
        insumo_id INTEGER NOT NULL,
        quantidade REAL NOT NULL,
        FOREIGN KEY (produto_id) REFERENCES produtos(id),
        FOREIGN KEY (insumo_id) REFERENCES insumos(id)
    )
    """)

    # =============================
    # PRODUTOS DA LEADPAGE
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos_leadpage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        descricao TEXT,
        categoria TEXT,
        preco REAL NOT NULL,
        imagem TEXT,
        ativo INTEGER DEFAULT 1
        )
    """)

    # =============================
    # PRODUTOS ONLINE
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pedidos_online (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        nome_cliente TEXT,
        telefone TEXT,
        endereco TEXT,
        tipo_entrega TEXT,
        valor_produtos REAL,
        valor_entrega REAL,
        valor_total REAL,
        data_agendamento DATE
        hora_agendamento TEXT
        observacoes TEXT,
        status TEXT DEFAULT 'NOVO',
        data DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =============================
    # PRODUTOS ONLINE
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pedido_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        produto_id INTEGER,
        nome_produto TEXT,
        quantidade INTEGER,
        valor REAL
        )
    """)
    
    # =============================
    # PRECIFICAÇÃO
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS precificacao (
        produto_id INTEGER PRIMARY KEY,
        custo_total REAL,
        margem REAL,
        preco_venda REAL,
        markup REAL,
        retorno_percentual REAL,
        FOREIGN KEY (produto_id) REFERENCES produtos(id)
    )
    """)

    # =============================
    # Calendário
    # =============================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calendario_disponibilidade (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data DATE UNIQUE,
        disponivel INTEGER DEFAULT 1,
        limite_encomendas INTEGER DEFAULT 10,
        limite_por_hora INTEGER DEFAULT 3
        )
        """)

    # =============================
    # CONTAS FIXAS
    # =============================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contas_fixas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT,
        valor REAL
    )
    """)
    

    # adicionar coluna data_vencimento se não existir
    colunas = cursor.execute("PRAGMA table_info(contas_fixas)").fetchall()
    nomes = [c[1] for c in colunas]

    if "data_vencimento" not in nomes:
        cursor.execute("""
        ALTER TABLE contas_fixas
        ADD COLUMN data_vencimento DATE
        """)