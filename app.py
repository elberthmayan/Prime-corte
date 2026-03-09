import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import init_db, get_connection
from datetime import date
import sqlite3

app = Flask(__name__)
app.secret_key = "barbearia_super_secreta_123"

# CONFIGURAÇÃO DE UPLOAD DE IMAGENS
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'profissionais')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

init_db()

HORARIOS_PADRAO = ["08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00"]

def usuario_logado(): return "user_id" in session
def admin_logado(): return "user_id" in session and session.get("user_tipo") == "admin"

def buscar_servicos(apenas_ativos=True):
    conn = get_connection(); cursor = conn.cursor()
    if apenas_ativos:
        cursor.execute("SELECT id, nome, descricao, valor, ativo FROM services WHERE ativo = 1 ORDER BY nome ASC")
    else:
        cursor.execute("SELECT id, nome, descricao, valor, ativo FROM services ORDER BY nome ASC")
    servicos = cursor.fetchall(); conn.close()
    return servicos

def get_profissionais_ativos():
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT id, nome, foto FROM profissionais WHERE ativo = 1 ORDER BY nome ASC")
    profs = cursor.fetchall(); conn.close()
    return profs

def get_todos_profissionais():
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT id, nome, foto, ativo FROM profissionais ORDER BY nome ASC")
    profs = cursor.fetchall(); conn.close()
    return profs

@app.route("/")
def index(): return render_template("index.html")

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefone = request.form.get("telefone", "").strip()
        senha = request.form.get("senha", "").strip()
        confirmar_senha = request.form.get("confirmar_senha", "").strip()
        
        if not nome or not email or not senha or not confirmar_senha:
            flash("Preencha todos os campos obrigatórios.", "error"); return redirect(url_for("cadastro"))
        if senha != confirmar_senha:
            flash("As senhas não coincidem.", "error"); return redirect(url_for("cadastro"))

        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close(); flash("Já existe uma conta com este e-mail.", "error"); return redirect(url_for("cadastro"))

        cursor.execute("INSERT INTO users (nome, email, telefone, senha, tipo) VALUES (?, ?, ?, ?, ?)", (nome, email, telefone, generate_password_hash(senha), "cliente"))
        conn.commit(); conn.close(); flash("Cadastro realizado com sucesso! Faça login.", "success")
        return redirect(url_for("login"))
    return render_template("cadastro.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email, senha = request.form.get("email", "").strip().lower(), request.form.get("senha", "").strip()
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id, nome, email, senha, tipo FROM users WHERE email = ?", (email,))
        usuario = cursor.fetchone(); conn.close()

        if not usuario or not check_password_hash(usuario["senha"], senha):
            flash("E-mail ou senha inválidos.", "error"); return redirect(url_for("login"))

        session["user_id"], session["user_nome"], session["user_email"], session["user_tipo"] = usuario["id"], usuario["nome"], usuario["email"], usuario["tipo"]
        flash("Login realizado com sucesso!", "success")
        return redirect(url_for("admin_agendamentos") if usuario["tipo"] == "admin" else url_for("cliente_agendamentos"))
    return render_template("login.html")

@app.route("/logout")
def logout(): session.clear(); flash("Sessão terminada.", "success"); return redirect(url_for("index"))

@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    if not usuario_logado(): return redirect(url_for("login"))
    conn = get_connection(); cursor = conn.cursor()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefone = request.form.get("telefone", "").strip()
        nova_senha = request.form.get("nova_senha", "").strip()
        
        cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, session["user_id"]))
        if cursor.fetchone(): 
            flash("Este e-mail já está a ser usado.", "error")
        else:
            if nova_senha: 
                cursor.execute("UPDATE users SET nome = ?, email = ?, telefone = ?, senha = ? WHERE id = ?", (nome, email, telefone, generate_password_hash(nova_senha), session["user_id"]))
            else: 
                cursor.execute("UPDATE users SET nome = ?, email = ?, telefone = ? WHERE id = ?", (nome, email, telefone, session["user_id"]))
            conn.commit(); session["user_nome"], session["user_email"] = nome, email; flash("Perfil atualizado!", "success")
            
    cursor.execute("SELECT nome, email, telefone FROM users WHERE id = ?", (session["user_id"],)); usuario = cursor.fetchone(); conn.close()
    return render_template("perfil.html", usuario=usuario)

@app.route("/mensagens")
def mensagens():
    if not usuario_logado(): return redirect(url_for("login"))
    conn = get_connection(); cursor = conn.cursor()
    if admin_logado(): cursor.execute("SELECT id, nome, email FROM users WHERE tipo = 'cliente' ORDER BY nome ASC")
    else: cursor.execute("SELECT id, nome, email FROM users WHERE tipo = 'admin' ORDER BY nome ASC")
    contatos = cursor.fetchall(); conn.close()
    return render_template("mensagens.html", contatos=contatos)

@app.route("/api/mensagens/<int:outro_id>", methods=["GET", "POST"])
def api_mensagens(outro_id):
    if not usuario_logado(): return jsonify({"error": "Não autorizado"}), 403
    meu_id = session["user_id"]; conn = get_connection(); cursor = conn.cursor()
    if request.method == "POST":
        mensagem = request.get_json().get("mensagem", "").strip()
        if mensagem:
            cursor.execute("INSERT INTO user_messages (remetente_id, destinatario_id, mensagem) VALUES (?, ?, ?)", (meu_id, outro_id, mensagem))
            conn.commit()
        conn.close(); return jsonify({"success": True})
    cursor.execute("""
        SELECT m.id, m.mensagem, m.created_at, m.remetente_id, u.nome as remetente_nome 
        FROM user_messages m JOIN users u ON m.remetente_id = u.id
        WHERE (m.remetente_id = ? AND m.destinatario_id = ?) OR (m.remetente_id = ? AND m.destinatario_id = ?)
        ORDER BY m.created_at ASC
    """, (meu_id, outro_id, outro_id, meu_id))
    mensagens = [{"id": r["id"], "mensagem": r["mensagem"], "created_at": r["created_at"], "is_mine": (r["remetente_id"] == meu_id), "remetente_nome": r["remetente_nome"]} for r in cursor.fetchall()]
    
    cursor.execute("SELECT nome FROM users WHERE id = ?", (outro_id,))
    contato_db = cursor.fetchone()
    contato_nome = contato_db["nome"] if contato_db else "Utilizador Removido"
    conn.close()
    return jsonify({"mensagens": mensagens, "contato_nome": contato_nome})

@app.route("/agendar", methods=["GET", "POST"])
def agendar():
    if not usuario_logado(): return redirect(url_for("login"))
    servicos = buscar_servicos(apenas_ativos=True)
    profissionais = get_profissionais_ativos()
    
    if request.method == "POST":
        servico, profissional, data_ag, horario, obs = request.form.get("servico"), request.form.get("profissional"), request.form.get("data"), request.form.get("horario"), request.form.get("observacao")
        try:
            if date.fromisoformat(data_ag) < date.today():
                flash("Data inválida.", "error"); return redirect(url_for("agendar"))
        except ValueError: 
            flash("Data inválida.", "error"); return redirect(url_for("agendar"))
            
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id FROM appointments WHERE profissional = ? AND data = ? AND horario = ? AND status IN ('agendado', 'confirmado')", (profissional, data_ag, horario))
        if cursor.fetchone():
            conn.close(); flash("Horário ocupado.", "error"); return redirect(url_for("agendar"))
        cursor.execute("INSERT INTO appointments (user_id, servico, profissional, data, horario, observacao, status) VALUES (?, ?, ?, ?, ?, ?, ?)", (session["user_id"], servico, profissional, data_ag, horario, obs, "agendado"))
        conn.commit(); conn.close(); flash("Agendado com sucesso!", "success"); return redirect(url_for("cliente_agendamentos"))
    return render_template("cliente/agendar.html", horarios=HORARIOS_PADRAO, profissionais=profissionais, servicos=servicos)

@app.route("/cliente/agendamentos")
def cliente_agendamentos():
    if not usuario_logado(): return redirect(url_for("login"))
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT id, servico, profissional, data, horario, observacao, status FROM appointments WHERE user_id = ? ORDER BY data ASC, horario ASC", (session["user_id"],))
    agendamentos = cursor.fetchall(); conn.close()
    return render_template("cliente/agendamentos.html", agendamentos=agendamentos)

@app.route("/cliente/agendamento/reagendar/<int:agendamento_id>", methods=["GET", "POST"])
def cliente_reagendar_agendamento(agendamento_id):
    if not usuario_logado(): return redirect(url_for("login"))
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments WHERE id = ? AND user_id = ?", (agendamento_id, session["user_id"]))
    agendamento = cursor.fetchone()
    
    if request.method == "POST" and agendamento:
        nova_data, novo_horario = request.form.get("data"), request.form.get("horario")
        try:
            if date.fromisoformat(nova_data) < date.today():
                flash("A nova data não pode estar no passado.", "error"); conn.close()
                return redirect(url_for("cliente_reagendar_agendamento", agendamento_id=agendamento_id))
        except ValueError: 
            flash("Data inválida.", "error"); conn.close()
            return redirect(url_for("cliente_reagendar_agendamento", agendamento_id=agendamento_id))
            
        cursor.execute("SELECT id FROM appointments WHERE profissional = ? AND data = ? AND horario = ? AND status IN ('agendado', 'confirmado') AND id != ?", (agendamento["profissional"], nova_data, novo_horario, agendamento_id))
        if cursor.fetchone():
            flash("Este horário já está ocupado. Escolha outro.", "error"); conn.close()
            return redirect(url_for("cliente_reagendar_agendamento", agendamento_id=agendamento_id))

        cursor.execute("UPDATE appointments SET data = ?, horario = ?, status = 'agendado' WHERE id = ?", (nova_data, novo_horario, agendamento_id))
        conn.commit(); conn.close(); flash("Reagendado com sucesso!", "success"); return redirect(url_for("cliente_agendamentos"))
    
    conn.close()
    return render_template("cliente/reagendar.html", agendamento=agendamento, horarios=HORARIOS_PADRAO)

@app.route("/cliente/agendamento/cancelar/<int:id>")
def cliente_cancelar_agendamento(id):
    if not usuario_logado(): return redirect(url_for("login"))
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = 'cancelado' WHERE id = ? AND user_id = ?", (id, session["user_id"]))
    conn.commit(); conn.close()
    flash("Agendamento cancelado.", "success")
    return redirect(url_for("cliente_agendamentos"))

@app.route("/admin/agendamentos")
def admin_agendamentos():
    if not admin_logado(): return redirect(url_for("login"))
    f_status, f_data, f_prof, f_cli = request.args.get("status"), request.args.get("data"), request.args.get("profissional"), request.args.get("cliente")
    conn = get_connection(); cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as t FROM appointments"); total_agendamentos = cursor.fetchone()["t"]
    cursor.execute("SELECT COUNT(*) as t FROM appointments WHERE date(created_at) = date('now')"); total_hoje = cursor.fetchone()["t"]
    cursor.execute("SELECT COUNT(*) as t FROM appointments WHERE status = 'agendado'"); total_agendado = cursor.fetchone()["t"]
    cursor.execute("SELECT COUNT(*) as t FROM appointments WHERE status = 'confirmado'"); total_confirmado = cursor.fetchone()["t"]
    cursor.execute("SELECT COUNT(*) as t FROM appointments WHERE status = 'cancelado'"); total_cancelado = cursor.fetchone()["t"]

    query = "SELECT a.*, u.nome AS cliente_nome FROM appointments a LEFT JOIN users u ON a.user_id = u.id WHERE 1=1"
    params = []
    if f_status: query += " AND a.status = ?"; params.append(f_status)
    if f_data: query += " AND a.data = ?"; params.append(f_data)
    if f_prof: query += " AND a.profissional = ?"; params.append(f_prof)
    if f_cli: query += " AND u.nome LIKE ?"; params.append(f"%{f_cli}%")
    cursor.execute(query + " ORDER BY a.data ASC", params)
    agendamentos = cursor.fetchall(); conn.close()
    
    return render_template("admin/agendamentos.html", agendamentos=agendamentos, total_agendamentos=total_agendamentos, total_hoje=total_hoje, total_agendado=total_agendado, total_confirmado=total_confirmado, total_cancelado=total_cancelado)

@app.route("/admin/agendamento/confirmar/<int:id>")
def admin_confirmar_agendamento(id):
    if not admin_logado(): return redirect(url_for("login"))
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = 'confirmado' WHERE id = ?", (id,))
    conn.commit(); conn.close(); flash("Agendamento confirmado!", "success")
    return redirect(request.referrer or url_for("admin_agendamentos"))

@app.route("/admin/agendamento/cancelar/<int:id>")
def admin_cancelar_agendamento(id):
    if not admin_logado(): return redirect(url_for("login"))
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = 'cancelado' WHERE id = ?", (id,))
    conn.commit(); conn.close(); flash("Agendamento cancelado!", "error")
    return redirect(request.referrer or url_for("admin_agendamentos"))

@app.route("/admin/agendamento/excluir/<int:id>")
def admin_excluir_agendamento(id):
    if not admin_logado(): return redirect(url_for("login"))
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = ?", (id,))
    conn.commit(); conn.close(); flash("Agendamento apagado definitivamente!", "success")
    return redirect(request.referrer or url_for("admin_agendamentos"))

@app.route("/admin/servicos")
def admin_servicos():
    if not admin_logado(): return redirect(url_for("login"))
    return render_template("admin/servicos.html", servicos=buscar_servicos(apenas_ativos=False))

@app.route("/admin/servicos/novo", methods=["GET", "POST"])
def admin_novo_servico():
    if not admin_logado(): return redirect(url_for("login"))
    if request.method == "POST":
        nome, desc, valor = request.form.get("nome"), request.form.get("descricao"), request.form.get("valor", 0.0) 
        conn = get_connection()
        try:
            conn.execute("INSERT INTO services (nome, descricao, valor, ativo) VALUES (?, ?, ?, 1)", (nome, desc, float(valor)))
            conn.commit(); flash("Serviço criado com sucesso!", "success")
        except sqlite3.IntegrityError: flash("Erro: Já existe um serviço registado com este nome.", "error")
        finally: conn.close()
        return redirect(url_for("admin_servicos"))
    return render_template("admin/servico_form.html", modo="novo")

@app.route("/admin/servicos/editar/<int:id>", methods=["GET", "POST"])
def admin_editar_servico(id):
    if not admin_logado(): return redirect(url_for("login"))
    conn = get_connection(); cursor = conn.cursor()
    if request.method == "POST":
        nome, desc, valor = request.form.get("nome"), request.form.get("descricao"), request.form.get("valor", 0.0)
        try:
            cursor.execute("UPDATE services SET nome = ?, descricao = ?, valor = ? WHERE id = ?", (nome, desc, float(valor), id))
            conn.commit(); flash("Serviço atualizado!", "success")
        except sqlite3.IntegrityError: flash("Erro: Já existe um serviço com este nome.", "error")
        finally: conn.close()
        return redirect(url_for("admin_servicos"))
    cursor.execute("SELECT * FROM services WHERE id = ?", (id,)); servico = cursor.fetchone(); conn.close()
    return render_template("admin/servico_form.html", modo="editar", servico=servico)

@app.route("/admin/servicos/inativar/<int:id>")
def admin_inativar_servico(id):
    if not admin_logado(): return redirect(url_for("login"))
    conn = get_connection(); conn.execute("UPDATE services SET ativo = 0 WHERE id = ?", (id,)); conn.commit(); conn.close()
    return redirect(url_for("admin_servicos"))

@app.route("/admin/servicos/reativar/<int:id>")
def admin_reativar_servico(id):
    if not admin_logado(): return redirect(url_for("login"))
    conn = get_connection(); conn.execute("UPDATE services SET ativo = 1 WHERE id = ?", (id,)); conn.commit(); conn.close()
    return redirect(url_for("admin_servicos"))

# --- ROTAS DE PROFISSIONAIS MELHORADAS ---
@app.route("/admin/profissionais")
def admin_profissionais():
    if not admin_logado(): return redirect(url_for("login"))
    return render_template("admin/profissionais.html", profissionais=get_todos_profissionais())

@app.route("/admin/profissionais/novo", methods=["POST"])
def admin_novo_profissional():
    if not admin_logado(): return redirect(url_for("login"))
    nome = request.form.get("nome", "").strip()
    
    # Tratamento de Imagem
    foto_arquivo = request.files.get("foto")
    filename = None
    if foto_arquivo and foto_arquivo.filename:
        filename = secure_filename(foto_arquivo.filename)
        foto_arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
    if nome:
        conn = get_connection()
        try:
            conn.execute("INSERT INTO profissionais (nome, foto) VALUES (?, ?)", (nome, filename))
            conn.commit(); flash(f"O(a) barbeiro(a) {nome} agora faz parte da equipa!", "success")
        except: flash("Erro: Já existe um profissional registado com esse nome.", "error")
        conn.close()
    return redirect(url_for("admin_profissionais"))

@app.route("/admin/profissionais/editar/<int:id>", methods=["GET", "POST"])
def admin_editar_profissional(id):
    if not admin_logado(): return redirect(url_for("login"))
    conn = get_connection(); cursor = conn.cursor()
    
    if request.method == "POST":
        novo_nome = request.form.get("nome", "").strip()
        foto_arquivo = request.files.get("foto")
        
        if novo_nome:
            try:
                if foto_arquivo and foto_arquivo.filename:
                    filename = secure_filename(foto_arquivo.filename)
                    foto_arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    cursor.execute("UPDATE profissionais SET nome = ?, foto = ? WHERE id = ?", (novo_nome, filename, id))
                else:
                    cursor.execute("UPDATE profissionais SET nome = ? WHERE id = ?", (novo_nome, id))
                conn.commit(); flash("Perfil do profissional atualizado com sucesso!", "success")
            except sqlite3.IntegrityError: flash("Já existe um profissional com este nome.", "error")
        conn.close()
        return redirect(url_for("admin_profissionais"))
        
    cursor.execute("SELECT id, nome, foto FROM profissionais WHERE id = ?", (id,)); profissional = cursor.fetchone(); conn.close()
    if not profissional: return redirect(url_for("admin_profissionais"))
    return render_template("admin/profissional_form.html", prof=profissional)

@app.route("/admin/profissionais/status/<int:id>/<int:ativo>")
def admin_status_profissional(id, ativo):
    if not admin_logado(): return redirect(url_for("login"))
    conn = get_connection()
    conn.execute("UPDATE profissionais SET ativo = ? WHERE id = ?", (ativo, id))
    conn.commit(); conn.close(); flash("Status do profissional atualizado!", "success")
    return redirect(url_for("admin_profissionais"))

@app.route("/api/horarios-disponiveis")
def horarios_disponiveis():
    p, d, i = request.args.get("profissional"), request.args.get("data"), request.args.get("ignorar_id")
    conn = get_connection(); cursor = conn.cursor()
    q = "SELECT horario FROM appointments WHERE profissional = ? AND data = ? AND status IN ('agendado', 'confirmado')"
    if i: cursor.execute(q + " AND id != ?", (p, d, i))
    else: cursor.execute(q, (p, d))
    ocupados = [r["horario"] for r in cursor.fetchall()]; conn.close()
    return jsonify({"horarios_disponiveis": [h for h in HORARIOS_PADRAO if h not in ocupados]})

if __name__ == "__main__": app.run(host="0.0.0.0", port=5000, debug=True)