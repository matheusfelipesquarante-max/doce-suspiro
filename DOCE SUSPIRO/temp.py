from database import conectar

conn = conectar()

# renomeia a tabela antiga
conn.execute("""
ALTER TABLE usuarios RENAME TO usuarios_old
""")

# cria nova tabela com regra correta
conn.execute("""
CREATE TABLE usuarios (
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

# copia os dados
conn.execute("""
INSERT INTO usuarios
(id,nome,usuario,senha,celular,cep,endereco,numero,bairro,nivel)
SELECT
id,nome,usuario,senha,celular,cep,endereco,numero,bairro,nivel
FROM usuarios_old
""")

# remove tabela antiga
conn.execute("DROP TABLE usuarios_old")

conn.commit()
conn.close()