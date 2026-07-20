// Файл: web/frontend/js/router.js
// Hash-роутер [feature 015, FR-012].
//
// Точное сопоставление маршрута (якоря ^...$, НЕ подстрока — R-UI-3 по духу), стек истории
// экранов + tg.BackButton, переходы без перезагрузки страницы. Неизвестный маршрут -> fallback
// (по умолчанию dashboard). Hash-маршрутизация не требует серверных fallback-роутов —
// статика веб-моста остаётся нетронутой.

const tg = window.Telegram && window.Telegram.WebApp;

const routes = [];
let notFoundHandler = null;
const stack = [];
let current = null;

function compile(pattern, handler) {
    const names = [];
    const source = pattern.replace(/:[^/]+/g, (m) => {
        names.push(m.slice(1));
        return "([^/]+)";
    });
    return { rx: new RegExp("^" + source + "$"), names, handler, pattern };
}

/** Регистрирует маршрут. pattern вида "#/event/:id". */
export function register(pattern, handler) {
    routes.push(compile(pattern, handler));
}

/** Обработчик неизвестного маршрута (обычно возврат на dashboard). */
export function setNotFound(handler) {
    notFoundHandler = handler;
}

function matchRoute(hash) {
    for (const route of routes) {
        const m = route.rx.exec(hash);
        if (m) {
            const params = {};
            route.names.forEach((name, i) => {
                params[name] = decodeURIComponent(m[i + 1]);
            });
            return { handler: route.handler, params };
        }
    }
    return null;
}

function renderHash(hash) {
    current = hash;
    const found = matchRoute(hash);
    if (found) {
        found.handler(found.params);
    } else if (notFoundHandler) {
        notFoundHandler(hash);
    }
    updateBackButton();
}

/** Переход на маршрут с добавлением текущего в стек истории. */
export function navigate(hash) {
    if (current && current !== hash) {
        stack.push(current);
    }
    if (location.hash === hash) {
        renderHash(hash); // тот же hash — hashchange не выстрелит, рендерим сами
    } else {
        location.hash = hash; // выстрелит hashchange -> renderHash
    }
}

/** Назад по стеку истории экранов. */
export function back() {
    if (stack.length === 0) return;
    const prev = stack.pop();
    current = null; // renderHash не путш'ит; back не должен добавлять в стек
    if (location.hash === prev) {
        renderHash(prev);
    } else {
        location.hash = prev;
    }
}

/** Запуск: подписка на hashchange + BackButton, первичный рендер. */
export function start(defaultHash = "#/dashboard") {
    window.addEventListener("hashchange", () => renderHash(location.hash || defaultHash));
    if (tg && tg.BackButton) {
        tg.BackButton.onClick(back);
    }
    renderHash(location.hash || defaultHash);
}

function updateBackButton() {
    if (!tg || !tg.BackButton) return;
    if (stack.length > 0) {
        tg.BackButton.show();
    } else {
        tg.BackButton.hide();
    }
}
