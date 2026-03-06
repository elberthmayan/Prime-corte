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

def _column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(column["name"] == column_name for column in columns)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
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

    # NOVO: Tabela Global de Mensagens (Pique WhatsApp)
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

    if not _column_exists(cursor, "appointments", "user_id"):
        cursor.execute("ALTER TABLE appointments ADD COLUMN user_id INTEGER")
    if not _column_exists(cursor, "appointments", "status"):
        cursor.execute("ALTER TABLE appointments ADD COLUMN status TEXT NOT NULL DEFAULT 'agendado'")

    admin_email = "admin@primecorte.com"
    admin_senha = generate_password_hash("admin123")
    cursor.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
    admin = cursor.fetchone()
    if not admin:
        cursor.execute("INSERT INTO users (nome, email, senha, tipo) VALUES (?, ?, ?, ?)", 
                       ("Administrador", admin_email, admin_senha, "admin"))

    servicos_padrao = [
        ("Corte", "Corte masculino com acabamento preciso."),
        ("Corte + Barba", "Combo clássico para sair alinhado."),
        ("Barba", "Desenho, alinhamento e finalização da barba."),
        ("Sobrancelha", "Ajuste fino para um visual mais limpo.")
    ]
    for nome, descricao in servicos_padrao:
        cursor.execute("SELECT id FROM services WHERE nome = ?", (nome,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO services (nome, descricao, ativo) VALUES (?, ?, 1)", (nome, descricao))

    conn.commit()
    conn.close()