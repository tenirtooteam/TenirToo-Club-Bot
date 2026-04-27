/* Файл: web/frontend/app.js */
const tg = window.Telegram.WebApp;

// Инициализация
tg.ready();
tg.expand();

const urlParams = new URLSearchParams(window.location.search);
const annId = urlParams.get('ann_id');

const elements = {
    loader: document.getElementById('main-loader'),
    content: document.getElementById('content'),
    errorScreen: document.getElementById('error-screen'),
    title: document.getElementById('event-title'),
    dates: document.getElementById('event-dates'),
    participants: document.getElementById('participants-count'),
    btn: document.getElementById('toggle-btn'),
    btnText: document.getElementById('btn-text'),
    errorMsg: document.getElementById('error-msg'),
    viewDetails: document.getElementById('view-details'),
    viewDashboard: document.getElementById('view-dashboard')
};

async function loadData() {
    if (!annId) {
        showDashboard();
        return;
    }

    try {
        const response = await fetch(`/api/announcements/${annId}`, {
            headers: {
                'X-TG-Init-Data': tg.initData
            }
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Ошибка загрузки");
        }

        const data = await response.json();
        renderEvent(data);
    } catch (err) {
        showError(err.message);
    }
}

function showDashboard() {
    elements.viewDetails.classList.add('hidden');
    elements.viewDashboard.classList.remove('hidden');
    elements.loader.classList.add('hidden');
    elements.content.classList.remove('hidden');
}

function renderEvent(data) {
    elements.title.innerText = data.title;
    elements.dates.innerText = `${data.start_date} — ${data.end_date || '?'}`;
    elements.participants.innerText = data.participants_count;
    
    updateButton(data.is_participant);
    
    elements.viewDashboard.classList.add('hidden');
    elements.viewDetails.classList.remove('hidden');
    elements.loader.classList.add('hidden');
    elements.content.classList.remove('hidden');
}

function updateButton(isParticipant) {
    if (isParticipant) {
        elements.btn.classList.add('joined');
        elements.btnText.innerText = "Вы участвуете (Отменить)";
    } else {
        elements.btn.classList.remove('joined');
        elements.btnText.innerText = "Записаться";
    }
}

async function toggleParticipation() {
    tg.HapticFeedback.impactOccurred('medium');
    elements.btn.disabled = true;
    elements.btn.style.opacity = "0.7";

    try {
        const response = await fetch(`/api/announcements/${annId}/toggle`, {
            method: 'POST',
            headers: {
                'X-TG-Init-Data': tg.initData
            }
        });

        const result = await response.json();
        if (result.success) {
            tg.HapticFeedback.notificationOccurred('success');
            // Перезагружаем данные для обновления счетчика и статуса
            await loadData();
        } else {
            tg.showAlert(result.message);
        }
    } catch (err) {
        tg.showAlert("Произошла ошибка");
    } finally {
        elements.btn.disabled = false;
        elements.btn.style.opacity = "1";
    }
}

function showError(msg) {
    elements.loader.classList.add('hidden');
    elements.content.classList.add('hidden');
    elements.errorScreen.classList.remove('hidden');
    elements.errorMsg.innerText = msg;
}

elements.btn.onclick = toggleParticipation;

// Загрузка
loadData();
