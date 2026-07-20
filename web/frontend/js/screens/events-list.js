// Файл: web/frontend/js/screens/events-list.js
// Экран списка походов [feature 015 US3]: клик по элементу -> карточка события.
import { h, mount } from "../render.js";
import { api } from "../api.js";
import * as router from "../router.js";
import { root, showLoading, showError } from "./shell.js";

const tg = window.Telegram && window.Telegram.WebApp;

function eventRow(e) {
    return h("div", {
        class: "list-item clickable-event",
        onClick: () => {
            if (tg && tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
            router.navigate(`#/event/${e.id}`);
        },
    },
        h("div", { class: "list-item-content" },
            h("h4", {}, e.title),
            h("p", {}, `${e.date} • ${e.participants_count} участников`)
        ),
        h("div", { class: "list-item-arrow" }, e.is_participant ? "✅" : "→")
    );
}

export async function render() {
    showLoading();
    try {
        const events = await api.get("/api/dashboard/events");
        const body = events.length === 0
            ? h("div", { class: "empty-state" }, "Пока нет активных мероприятий.")
            : h("div", { class: "list-container" }, events.map(eventRow));
        // Создание доступно любому авторизованному (паритет с ботом, без admin-гейта).
        const createBtn = h("button", {
            class: "create-btn",
            onClick: () => {
                if (tg && tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
                router.navigate("#/event/new");
            },
        }, "➕ Новый поход");
        mount(root(),
            h("div", { class: "view" },
                h("header", { class: "sub-header" }, h("h2", {}, "🏔 Все походы")),
                h("main", {}, createBtn, body)
            )
        );
    } catch (err) {
        showError(err.message);
    }
}
