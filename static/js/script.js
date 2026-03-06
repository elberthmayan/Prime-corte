// Funcionalidade de Mostrar/Ocultar Senha ( Função do Olhinho)
const togglePasswordBtns = document.querySelectorAll('.toggle-password');
togglePasswordBtns.forEach(btn => {
    btn.addEventListener('click', function() {
        const input = this.previousElementSibling;
        const icon = this.querySelector('i');
        if (input.type === 'password') {
            input.type = 'text';
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        } else {
            input.type = 'password';
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    });
});

// ==========================================
// ==========================================
// CHAT GLOBAL (PIQUE WHATSAPP)
// ==========================================
const waContacts = document.querySelectorAll('.wa-contact');
const waSidebar = document.getElementById('wa-sidebar');
const waChatArea = document.getElementById('wa-chat-area');
const waChatHeader = document.getElementById('wa-chat-header');
const waChatPlaceholder = document.getElementById('wa-chat-placeholder');
const waChatMessages = document.getElementById('wa-chat-messages');
const waChatInputArea = document.getElementById('wa-chat-input-area');
const waChatTitle = document.getElementById('wa-chat-title');
const waMsgInput = document.getElementById('wa-msg-input');
const waBtnSend = document.getElementById('wa-btn-send');
const btnBackChat = document.getElementById('btn-back-chat');

let currentChatUserId = null;
let chatGlobalInterval = null;

waContacts.forEach(contact => {
    contact.addEventListener('click', function() {
        waContacts.forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        
        currentChatUserId = this.getAttribute('data-id');
        waChatTitle.textContent = this.querySelector('h4').textContent;
        
        // Esconde placeholder, mostra chat
        waChatPlaceholder.style.display = 'none';
        waChatHeader.style.display = 'flex';
        waChatMessages.style.display = 'flex';
        waChatInputArea.style.display = 'flex';

        // Responsivo: no celular esconde a lista e mostra o chat
        if(window.innerWidth <= 800) {
            waSidebar.style.display = 'none';
            waChatArea.style.display = 'flex';
        }

        carregarMensagensGlobais();
        clearInterval(chatGlobalInterval);
        chatGlobalInterval = setInterval(carregarMensagensGlobais, 3000);
    });
});

if(btnBackChat) {
    btnBackChat.addEventListener('click', () => {
        waSidebar.style.display = 'flex';
        waChatArea.style.display = 'none';
        clearInterval(chatGlobalInterval);
        currentChatUserId = null;
    });
}

async function carregarMensagensGlobais() {
    if (!currentChatUserId) return;
    try {
        const response = await fetch(`/api/mensagens/${currentChatUserId}`);
        const data = await response.json();
        
        if (data.mensagens) {
            const isAtBottom = waChatMessages.scrollHeight - waChatMessages.scrollTop <= waChatMessages.clientHeight + 50;
            waChatMessages.innerHTML = '';
            
            if (data.mensagens.length === 0) {
                waChatMessages.innerHTML = '<p style="text-align:center; color:var(--muted); margin-top:auto; margin-bottom:auto;">Nenhuma mensagem ainda.</p>';
            } else {
                data.mensagens.forEach(msg => {
                    const div = document.createElement('div');
                    div.className = msg.is_mine ? 'wa-msg wa-mine' : 'wa-msg wa-theirs';
                    const time = new Date(msg.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    div.innerHTML = `<span>${msg.mensagem}</span><small>${time}</small>`;
                    waChatMessages.appendChild(div);
                });
            }
            if (isAtBottom) waChatMessages.scrollTop = waChatMessages.scrollHeight;
        }
    } catch (e) { console.error(e); }
}

async function enviarMensagemGlobal() {
    const texto = waMsgInput.value.trim();
    if (!texto || !currentChatUserId) return;
    waMsgInput.value = '';
    await fetch(`/api/mensagens/${currentChatUserId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensagem: texto })
    });
    carregarMensagensGlobais();
}

if(waBtnSend) {
    waBtnSend.addEventListener('click', enviarMensagemGlobal);
    waMsgInput.addEventListener('keypress', e => { if (e.key === 'Enter') enviarMensagemGlobal(); });
}
// ==========================================
// MODAL DE EXCLUSÃO PERSONALIZADO
// ==========================================
const deleteModal = document.getElementById('delete-modal');
const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
const cancelDeleteBtn = document.getElementById('cancel-delete');

document.querySelectorAll('.btn-open-delete-modal').forEach(btn => {
    btn.addEventListener('click', function() {
        // Pega no URL de exclusão que está escondido no botão
        const url = this.getAttribute('data-url');
        // Coloca o URL no botão vermelho do Modal
        confirmDeleteBtn.setAttribute('href', url);
        // Mostra o Modal no ecrã
        deleteModal.classList.add('active');
    });
});

if(cancelDeleteBtn) {
    cancelDeleteBtn.addEventListener('click', () => {
        deleteModal.classList.remove('active');
    });
}