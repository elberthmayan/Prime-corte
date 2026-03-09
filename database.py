import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "barbearia.db"

def get_connection():
    DB_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            telefone TEXT,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'cliente',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            valor REAL NOT NULL DEFAULT 0.0,
            ativo INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            servico TEXT NOT NULL,
            profissional TEXT NOT NULL,
            data TEXT NOT NULL,
            horario TEXT NOT NULL,
            observacao TEXT,
            status TEXT NOT NULL DEFAULT 'agendado',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            remetente_id INTEGER NOT NULL,
            destinatario_id INTEGER NOT NULL,
            mensagem TEXT NOT NULL,
            lida INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (remetente_id) REFERENCES users(id),
            FOREIGN KEY (destinatario_id) REFERENCES users(id)
        )
    """)

    # NOVIDADE AQUI: Adicionada a coluna "foto"
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profissionais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            foto TEXT DEFAULT NULL,
            ativo INTEGER NOT NULL DEFAULT 1
        )
    """)

    admin_email = "admin@primecorte.com"
    cursor.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (nome, email, telefone, senha, tipo) VALUES (?, ?, ?, ?, ?)", 
                       ("Administrador", admin_email, "", generate_password_hash("admin123"), "admin"))

    servicos_padrao = [
        ("Corte", "Corte masculino preciso.", 35.00),
        ("Corte + Barba", "Combo clássico.", 60.00),
        ("Barba", "Desenho e alinhamento.", 30.00)
    ]
    for n, d, v in servicos_padrao:
        cursor.execute("SELECT id FROM services WHERE nome = ?", (n,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO services (nome, descricao, valor, ativo) VALUES (?, ?, ?, 1)", (n, d, v))

    profissionais_padrao = ["André", "Carlos", "Mateus"]
    for p in profissionais_padrao:
        cursor.execute("SELECT id FROM profissionais WHERE nome = ?", (p,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO profissionais (nome) VALUES (?)", (p,))

    conn.commit()
    conn.close()