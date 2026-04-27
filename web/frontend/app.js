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
    errorMsg: document.getElementById('error-msg'),
    
    // View Details (Announcement)
    viewDetails: document.getElementById('view-details'),
    title: document.getElementById('event-title'),
    dates: document.getElementById('event-dates'),
    participants: document.getElementById('participants-count'),
    btn: document.getElementById('toggle-btn'),
    btnText: document.getElementById('btn-text'),
    
    // View Dashboard
    viewDashboard: document.getElementById('view-dashboard'),
    userName: document.getElementById('user-name'),
    countTopics: document.getElementById('count-topics'),
    countEvents: document.getElementById('count-events'),
    
    // View Lists
    viewTopics: document.getElementById('view-topics'),
    topicsList: document.getElementById('topics-list'),
    viewEvents: document.getElementById('view-events'),
    eventsList: document.getElementById('events-list'),
    viewProfile: document.getElementById('view-profile'),
    profileId: document.getElementById('profile-id'),
    profileName: document.getElementById('profile-name'),
    profileRoles: document.getElementById('profile-roles'),
    
    // Admin Views
    adminTopicsList: document.getElementById('admin-topics-list'),
    adminGroupsList: document.getElementById('admin-groups-list'),
    rolesFaqContent: document.getElementById('roles-faq-content'),
};

let currentView = 'view-dashboard';
const viewStack = [];
let activeEventId = null; // Текущий ID ивента для переключения участия

// --- API Helpers ---

async function apiFetch(url, method = 'GET') {
    const response = await fetch(url, {
        method,
        headers: {
            'X-TG-Init-Data': tg.initData
        }
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Ошибка API");
    }
    return await response.json();
}

// --- Navigation ---

function switchView(viewId, pushToStack = true) {
    // Скрываем все вьюхи
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    
    const target = document.getElementById(viewId);
    if (target) {
        target.classList.remove('hidden');
        if (pushToStack && currentView !== viewId) {
            viewStack.push(currentView);
        }
        currentView = viewId;
    }
    
    // Управление кнопкой Назад
    if (viewStack.length > 0) {
        tg.BackButton.show();
    } else {
        tg.BackButton.hide();
    }
    
    // Специфическая логика загрузки данных для вьюхи
    if (viewId === 'view-topics') loadTopics();
    if (viewId === 'view-profile') loadProfile();
    if (viewId === 'view-events') loadEvents();
    if (viewId === 'view-dashboard') loadDashboard();
    if (viewId === 'view-admin-topics') loadAdminTopics();
    if (viewId === 'view-admin-groups') loadAdminGroups();
    if (viewId === 'view-roles-faq') loadRolesFaq();
}

tg.BackButton.onClick(() => {
    if (viewStack.length > 0) {
        const prevView = viewStack.pop();
        switchView(prevView, false);
    }
});

// --- Data Loading ---

async function loadData() {
    if (annId) {
        try {
            const data = await apiFetch(`/api/announcements/${annId}`);
            activeEventId = data.event_id;
            renderEvent(data);
        } catch (err) {
            showError(err.message);
        }
    } else {
        switchView('view-dashboard', false);
    }
}

async function loadDashboard() {
    try {
        const data = await apiFetch('/api/dashboard/init');
        elements.userName.innerText = `Привет, ${data.name}!`;
        elements.countTopics.innerText = data.stats.topics_available;
        elements.countEvents.innerText = data.stats.events_active;
        
        if (data.is_admin) {
            document.querySelectorAll('.admin-only').forEach(el => el.classList.remove('hidden'));
        }
        
        elements.loader.classList.add('hidden');
        elements.content.classList.remove('hidden');
    } catch (err) {
        showError(err.message);
    }
}

async function loadTopics() {
    elements.topicsList.innerHTML = '<div class="spinner"></div>';
    try {
        const topics = await apiFetch('/api/dashboard/topics');
        if (topics.length === 0) {
            elements.topicsList.innerHTML = '<div class="empty-state">У вас пока нет доступа к топикам.</div>';
            return;
        }
        
        elements.topicsList.innerHTML = topics.map(t => `
            <div class="list-item">
                <div class="list-item-content">
                    <h4>${t.name}</h4>
                    <p>ID: ${t.id}</p>
                </div>
                <div class="list-item-arrow">→</div>
            </div>
        `).join('');
    } catch (err) {
        tg.showAlert("Не удалось загрузить топики");
    }
}

async function loadEvents() {
    elements.eventsList.innerHTML = '<div class="spinner"></div>';
    try {
        const events = await apiFetch('/api/dashboard/events');
        if (events.length === 0) {
            elements.eventsList.innerHTML = '<div class="empty-state">Пока нет активных мероприятий.</div>';
            return;
        }
        
        elements.eventsList.innerHTML = events.map(e => `
            <div class="list-item clickable-event" data-id="${e.id}">
                <div class="list-item-content">
                    <h4>${e.title}</h4>
                    <p>${e.date} • ${e.participants_count} участников</p>
                </div>
                <div class="list-item-arrow">${e.is_participant ? '✅' : '→'}</div>
            </div>
        `).join('');
        
        // Навешиваем клики
        document.querySelectorAll('.clickable-event').forEach(el => {
            el.onclick = () => {
                const id = el.getAttribute('data-id');
                viewEventDetails(id);
            };
        });
    } catch (err) {
        tg.showAlert("Ошибка загрузки мероприятий");
    }
}

async function viewEventDetails(eventId) {
    tg.HapticFeedback.selectionChanged();
    elements.loader.classList.remove('hidden');
    try {
        const data = await apiFetch(`/api/dashboard/events/${eventId}`);
        activeEventId = eventId;
        renderEvent(data);
    } catch (err) {
        tg.showAlert("Не удалось загрузить детали");
    } finally {
        elements.loader.classList.add('hidden');
    }
}

async function loadProfile() {
    try {
        const data = await apiFetch('/api/dashboard/profile');
        elements.profileId.innerText = data.user_id;
        elements.profileName.innerText = data.name;
        elements.profileRoles.innerHTML = data.roles.map(r => `
            <span class="role-tag">${r.name}${r.topic_id ? ' (T:'+r.topic_id+')' : ''}</span>
        `).join('');
    } catch (err) {
        tg.showAlert("Ошибка профиля");
    }
}

async function loadAdminTopics() {
    elements.adminTopicsList.innerHTML = '<div class="spinner"></div>';
    try {
        const topics = await apiFetch('/api/dashboard/admin/topics');
        elements.adminTopicsList.innerHTML = topics.map(t => `
            <div class="list-item">
                <div class="list-item-content">
                    <h4>${t.name}</h4>
                    <p>ID: ${t.id} • Глобальный доступ</p>
                </div>
            </div>
        `).join('');
    } catch (err) {
        tg.showAlert("Ошибка загрузки всех топиков");
    }
}

async function loadAdminGroups() {
    elements.adminGroupsList.innerHTML = '<div class="spinner"></div>';
    try {
        const groups = await apiFetch('/api/dashboard/admin/groups');
        elements.adminGroupsList.innerHTML = groups.map(g => `
            <div class="list-item">
                <div class="list-item-content">
                    <h4>${g.name}</h4>
                    <p>Группа/Шаблон доступа</p>
                </div>
            </div>
        `).join('');
    } catch (err) {
        tg.showAlert("Ошибка загрузки групп");
    }
}

async function loadRolesFaq() {
    elements.rolesFaqContent.innerHTML = '<div class="spinner"></div>';
    try {
        const data = await apiFetch('/api/dashboard/roles/faq');
        // Текст из бота приходит с HTML тегами, Telegram TMA поддерживает базовый рендеринг
        elements.rolesFaqContent.innerHTML = `<div class="faq-text">${data.text}</div>`;
    } catch (err) {
        tg.showAlert("Ошибка загрузки FAQ");
    }
}

// --- Event (Announcement) Rendering ---

function renderEvent(data) {
    elements.title.innerText = data.title;
    elements.dates.innerText = `${data.start_date} — ${data.end_date || '?'}`;
    elements.participants.innerText = data.participants_count;
    
    updateButton(data.is_participant);
    
    switchView('view-details', true);
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

    try {
        // Выбираем эндпоинт в зависимости от контекста (анонс или список)
        const endpoint = annId ? `/api/announcements/${annId}/toggle` : `/api/dashboard/events/${activeEventId}/toggle`;
        const result = await apiFetch(endpoint, 'POST');
        
        if (result.success) {
            tg.HapticFeedback.notificationOccurred('success');
            // Обновляем текущую вьюху
            if (annId) {
                await loadData();
            } else {
                await viewEventDetails(activeEventId);
            }
        } else {
            tg.showAlert(result.message);
        }
    } catch (err) {
        tg.showAlert("Произошла ошибка");
    } finally {
        elements.btn.disabled = false;
    }
}

// --- Initialization ---

function showError(msg) {
    elements.loader.classList.add('hidden');
    elements.content.classList.add('hidden');
    elements.errorScreen.classList.remove('hidden');
    elements.errorMsg.innerText = msg;
}

// Menu Click Handlers
document.querySelectorAll('.menu-item').forEach(item => {
    item.addEventListener('click', () => {
        const targetView = item.getAttribute('data-view');
        if (targetView) {
            tg.HapticFeedback.selectionChanged();
            switchView(targetView);
        }
    });
});

elements.btn.onclick = toggleParticipation;

// Start
loadData();
