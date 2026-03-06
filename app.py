from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import init_db, get_connection
from datetime import date

app = Flask(__name__)
app.secret_key = "prime_corte_secret_key"

init_db()

HORARIOS_PADRAO = ["08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00"]
PROFISSIONAIS = ["André", "Carlos", "Mateus"]

def usuario_logado(): return "user_id" in session
def admin_logado(): return "user_id" in session and session.get("user_tipo") == "admin"
def buscar_servicos_ativos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, descricao FROM services WHERE ativo = 1 ORDER BY nome ASC")
    servicos = cursor.fetchall()
    conn.close()
    return servicos

@app.route("/")
def index(): return render_template("index.html")

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome, email, senha, confirmar_senha = request.form.get("nome", "").strip(), request.form.get("email", "").strip().lower(), request.form.get("senha", "").strip(), request.form.get("confirmar_senha", "").strip()
        if not nome or not email or not senha or not confirmar_senha:
            flash("Preencha todos os campos.", "error")
            return redirect(url_for("cadastro"))
        if senha != confirmar_senha:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for("cadastro"))

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            flash("Já existe uma conta com este e-mail.", "error")
            return redirect(url_for("cadastro"))

        cursor.execute("INSERT INTO users (nome, email, senha, tipo) VALUES (?, ?, ?, ?)", (nome, email, generate_password_hash(senha), "cliente"))
        conn.commit()
        conn.close()
        flash("Cadastro realizado com sucesso! Faça login.", "success")
        return redirect(url_for("login"))
    return render_template("cadastro.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email, senha = request.form.get("email", "").strip().lower(), request.form.get("senha", "").strip()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, email, senha, tipo FROM users WHERE email = ?", (email,))
        usuario = cursor.fetchone()
        conn.close()

        if not usuario or not check_password_hash(usuario["senha"], senha):
            flash("E-mail ou senha inválidos.", "error")
            return redirect(url_for("login"))

        session["user_id"], session["user_nome"], session["user_email"], session["user_tipo"] = usuario["id"], usuario["nome"], usuario["email"], usuario["tipo"]
        flash("Login realizado com sucesso!", "success")
        return redirect(url_for("admin_agendamentos") if usuario["tipo"] == "admin" else url_for("cliente_agendamentos"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Sessão terminada.", "success")
    return redirect(url_for("index"))

# ==========================================
# NOVO: PERFIL (Caminho 3)
# ==========================================
@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    if not usuario_logado(): return redirect(url_for("login"))
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        nome, email, nova_senha = request.form.get("nome", "").strip(), request.form.get("email", "").strip().lower(), request.form.get("nova_senha", "").strip()
        cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, session["user_id"]))
        if cursor.fetchone():
            flash("Este e-mail já está sendo usado por outra conta.", "error")
        else:
            if nova_senha:
                cursor.execute("UPDATE users SET nome = ?, email = ?, senha = ? WHERE id = ?", (nome, email, generate_password_hash(nova_senha), session["user_id"]))
            else:
                cursor.execute("UPDATE users SET nome = ?, email = ? WHERE id = ?", (nome, email, session["user_id"]))
            conn.commit()
            session["user_nome"], session["user_email"] = nome, email
            flash("Perfil atualizado com sucesso!", "success")
            
    cursor.execute("SELECT nome, email FROM users WHERE id = ?", (session["user_id"],))
    usuario = cursor.fetchone()
    conn.close()
    return render_template("perfil.html", usuario=usuario)

# ==========================================
# NOVO: CHAT GLOBAL (Caminho 2)
# ==========================================
@app.route("/mensagens")
def mensagens():
    if not usuario_logado(): return redirect(url_for("login"))
    conn = get_connection()
    cursor = conn.cursor()
    
    # Se for admin, carrega clientes. Se for cliente, carrega admins.
    if admin_logado():
        cursor.execute("SELECT id, nome, email FROM users WHERE tipo = 'cliente' ORDER BY nome ASC")
    else:
        cursor.execute("SELECT id, nome, email FROM users WHERE tipo = 'admin' ORDER BY nome ASC")
    contatos = cursor.fetchall()
    conn.close()
    return render_template("mensagens.html", contatos=contatos)

@app.route("/api/mensagens/<int:outro_id>", methods=["GET", "POST"])
def api_mensagens(outro_id):
    if not usuario_logado(): return jsonify({"error": "Não autorizado"}), 403
    meu_id = session["user_id"]
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        mensagem = request.get_json().get("mensagem", "").strip()
        if mensagem:
            cursor.execute("INSERT INTO user_messages (remetente_id, destinatario_id, mensagem) VALUES (?, ?, ?)", (meu_id, outro_id, mensagem))
            conn.commit()
        conn.close()
        return jsonify({"success": True})

    cursor.execute("""
        SELECT m.id, m.mensagem, m.created_at, m.remetente_id, u.nome as remetente_nome 
        FROM user_messages m JOIN users u ON m.remetente_id = u.id
        WHERE (m.remetente_id = ? AND m.destinatario_id = ?) OR (m.remetente_id = ? AND m.destinatario_id = ?)
        ORDER BY m.created_at ASC
    """, (meu_id, outro_id, outro_id, meu_id))
    
    mensagens = [{"id": r["id"], "mensagem": r["mensagem"], "created_at": r["created_at"], "is_mine": (r["remetente_id"] == meu_id), "remetente_nome": r["remetente_nome"]} for r in cursor.fetchall()]
    
    cursor.execute("SELECT nome FROM users WHERE id = ?", (outro_id,))
    contato_nome = cursor.fetchone()["nome"]
    conn.close()
    return jsonify({"mensagens": mensagens, "contato_nome": contato_nome})


# ==========================================
# ROTAS DO CLIENTE
# ==========================================
@app.route("/agendar", methods=["GET", "POST"])
def agendar():
    if not usuario_logado(): return redirect(url_for("login"))
    servicos = buscar_servicos_ativos()
    conn = get_connection()
    cursor = conn.cursor()
    if request.method == "POST":
        servico, profissional, data, horario, observacao = request.form.get("servico", "").strip(), request.form.get("profissional", "").strip(), request.form.get("data", "").strip(), request.form.get("horario", "").strip(), request.form.get("observacao", "").strip()
        cursor.execute("SELECT id FROM appointments WHERE profissional = ? AND data = ? AND horario = ? AND status IN ('agendado', 'confirmado')", (profissional, data, horario))
        if cursor.fetchone():
            conn.close()
            flash("Este horário já está ocupado.", "error")
            return redirect(url_for("agendar"))
        cursor.execute("INSERT INTO appointments (user_id, servico, profissional, data, horario, observacao, status) VALUES (?, ?, ?, ?, ?, ?, ?)", (session["user_id"], servico, profissional, data, horario, observacao, "agendado"))
        conn.commit()
        conn.close()
        flash("Agendamento realizado!", "success")
        return redirect(url_for("cliente_agendamentos"))
    conn.close()
    return render_template("cliente/agendar.html", horarios=HORARIOS_PADRAO, profissionais=PROFISSIONAIS, servicos=servicos)

@app.route("/cliente/agendamentos")
def cliente_agendamentos():
    if not usuario_logado() or admin_logado(): return redirect(url_for("login"))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, servico, profissional, data, horario, observacao, status FROM appointments WHERE user_id = ? ORDER BY data ASC, horario ASC", (session["user_id"],))
    agendamentos = cursor.fetchall()
    conn.close()
    return render_template("cliente/agendamentos.html", agendamentos=agendamentos)

@app.route("/cliente/agendamento/cancelar/<int:agendamento_id>")
def cliente_cancelar_agendamento(agendamento_id):
    if not usuario_logado(): return redirect(url_for("login"))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = 'cancelado' WHERE id = ? AND user_id = ?", (agendamento_id, session["user_id"]))
    conn.commit()
    conn.close()
    flash("Cancelado com sucesso.", "success")
    return redirect(url_for("cliente_agendamentos"))

@app.route("/cliente/agendamento/reagendar/<int:agendamento_id>", methods=["GET", "POST"])
def cliente_reagendar_agendamento(agendamento_id):
    if not usuario_logado(): return redirect(url_for("login"))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments WHERE id = ? AND user_id = ?", (agendamento_id, session["user_id"]))
    agendamento = cursor.fetchone()
    if request.method == "POST" and agendamento:
        nova_data, novo_horario = request.form.get("data", "").strip(), request.form.get("horario", "").strip()
        cursor.execute("UPDATE appointments SET data = ?, horario = ?, status = 'agendado' WHERE id = ?", (nova_data, novo_horario, agendamento_id))
        conn.commit()
        flash("Reagendado com sucesso.", "success")
        return redirect(url_for("cliente_agendamentos"))
    conn.close()
    return render_template("cliente/reagendar.html", agendamento=agendamento, horarios=HORARIOS_PADRAO)

@app.route("/api/horarios-disponiveis")
def horarios_disponiveis():
    profissional, data, ignorar_id = request.args.get("profissional", ""), request.args.get("data", ""), request.args.get("ignorar_id", "")
    conn = get_connection()
    cursor = conn.cursor()
    if ignorar_id: cursor.execute("SELECT horario FROM appointments WHERE profissional = ? AND data = ? AND status IN ('agendado', 'confirmado') AND id != ?", (profissional, data, ignorar_id))
    else: cursor.execute("SELECT horario FROM appointments WHERE profissional = ? AND data = ? AND status IN ('agendado', 'confirmado')", (profissional, data))
    horarios_ocupados = [row["horario"] for row in cursor.fetchall()]
    conn.close()
    return jsonify({"horarios_disponiveis": [h for h in HORARIOS_PADRAO if h not in horarios_ocupados], "horarios_ocupados": horarios_ocupados})

# ==========================================
# ROTAS DO ADMIN
# ==========================================
@app.route("/admin/agendamentos")
def admin_agendamentos():
    if not admin_logado(): return redirect(url_for("login"))
    filtro_status, filtro_data, filtro_profissional, filtro_cliente = request.args.get("status", ""), request.args.get("data", ""), request.args.get("profissional", ""), request.args.get("cliente", "")
    conn = get_connection()
    cursor = conn.cursor()
    hoje = date.today().isoformat()
    cursor.execute("SELECT COUNT(*) AS total FROM appointments")
    total_agendamentos = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM appointments WHERE status = 'agendado'")
    total_agendado = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM appointments WHERE status = 'confirmado'")
    total_confirmado = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM appointments WHERE status = 'cancelado'")
    total_cancelado = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM appointments WHERE data = ? AND status IN ('agendado', 'confirmado')", (hoje,))
    total_hoje = cursor.fetchone()["total"]

    query = "SELECT a.id, a.servico, a.profissional, a.data, a.horario, a.observacao, a.status, u.nome AS cliente_nome FROM appointments a LEFT JOIN users u ON a.user_id = u.id WHERE 1=1"
    params = []
    if filtro_status: query += " AND a.status = ?"; params.append(filtro_status)
    if filtro_data: query += " AND a.data = ?"; params.append(filtro_data)
    if filtro_profissional: query += " AND a.profissional = ?"; params.append(filtro_profissional)
    if filtro_cliente: query += " AND u.nome LIKE ?"; params.append(f"%{filtro_cliente}%")
    query += " ORDER BY a.data ASC, a.horario ASC"
    cursor.execute(query, params)
    agendamentos = cursor.fetchall()
    conn.close()

    return render_template("admin/agendamentos.html", agendamentos=agendamentos, filtro_status=filtro_status, filtro_data=filtro_data, filtro_profissional=filtro_profissional, filtro_cliente=filtro_cliente, profissionais=PROFISSIONAIS, total_agendamentos=total_agendamentos, total_agendado=total_agendado, total_confirmado=total_confirmado, total_cancelado=total_cancelado, total_hoje=total_hoje)

@app.route("/admin/agendamento/confirmar/<int:agendamento_id>")
def admin_confirmar_agendamento(agendamento_id):
    if not admin_logado(): return redirect(url_for("login"))
    conn = get_connection()
    conn.execute("UPDATE appointments SET status = 'confirmado' WHERE id = ? AND status != 'cancelado'", (agendamento_id,))
    conn.commit(); conn.close()
    flash("Confirmado com sucesso.", "success")
    return redirect(url_for("admin_agendamentos"))

@app.route("/admin/agendamento/cancelar/<int:agendamento_id>")
def admin_cancelar_agendamento(agendamento_id):
    if not admin_logado(): return redirect(url_for("login"))
    conn = get_connection()
    conn.execute("UPDATE appointments SET status = 'cancelado' WHERE id = ?", (agendamento_id,))
    conn.commit(); conn.close()
    flash("Cancelado com sucesso.", "success")
    return redirect(url_for("admin_agendamentos"))

@app.route("/admin/agendamento/excluir/<int:agendamento_id>")
def admin_excluir_agendamento(agendamento_id):
    if not admin_logado(): return redirect(url_for("login"))
    conn = get_connection()
    conn.execute("DELETE FROM appointments WHERE id = ?", (agendamento_id,))
    conn.commit(); conn.close()
    flash("Agendamento excluído da base.", "success")
    return redirect(url_for("admin_agendamentos"))

@app.route("/admin/servicos")
def admin_servicos(): return render_template("admin/servicos.html", servicos=buscar_servicos_ativos())

if __name__ == "__main__": app.run(host="0.0.0.0", port=5000, debug=True)