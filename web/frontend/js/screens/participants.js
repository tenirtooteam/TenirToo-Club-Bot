// Файл: web/frontend/js/screens/participants.js
// Экран состава похода [feature 016 US3]: просмотр + снятие участника.
//
// Снятие требует ЯВНОГО подтверждения перед запросом (C2, R-DATA-4); отмена — состав не меняется,
// запрос не уходит. Организаторов из ростера не снимаем. Сервер — единственный авторитет: снятие
// идёт через feature 014 (remove-only, no-op для не-участника), устаревшее состояние безопасно.
import { h, mount } from "../render.js";
import { api } from "../api.js";
import { root, showLoading, showError } from "./shell.js";

const tg = window.Telegram && window.Telegram.WebApp;

function confirmRemove(name) {
    const message = `Убрать участника «${name}» из похода?`;
    return new Promise((resolve) => {
        if (tg && tg.showConfirm) {
            tg.showConfirm(message, (ok) => resolve(!!ok));
        } else {
            resolve(window.confirm(message)); // Level-B стенд без Telegram
        }
    });
}

async function removeParticipant(eventId, p) {
    const ok = await confirmRemove(p.display_name);
    if (!ok) return; // отмена — состав не меняется (C2)
    if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred("medium");
    try {
        const result = await api.del(`/api/moderation/events/${eventId}/participants/${p.user_id}`);
        if (!result.success && tg) tg.showAlert(result.message);
    } catch (err) {
        if (tg) tg.showAlert(err.message || "Произошла ошибка");
    }
    render(eventId); // перерисовываем свежим составом
}

function participantRow(eventId, p) {
    return h("div", { class: "list-item" },
        h("div", { class: "list-item-content" },
            h("h4", {}, p.display_name),
            p.is_organizer ? h("p", {}, "организатор") : null
        ),
        // Организаторов из ростера не снимаем — кнопка только у обычных участников.
        p.is_organizer ? null : h("button", {
            class: "remove-btn",
            onClick: () => removeParticipant(eventId, p),
        }, "Убрать")
    );
}

export async function render(eventId) {
    showLoading();
    try {
        const data = await api.get(`/api/moderation/events/${eventId}/participants`);
        const list = data.participants || [];
        const body = list.length === 0
            ? h("div", { class: "empty-state" }, "В походе пока нет участников.")
            : h("div", { class: "list-container" }, list.map((p) => participantRow(eventId, p)));
        mount(root(),
            h("div", { class: "view" },
                h("header", { class: "sub-header" },
                    h("h2", {}, "👥 Участники"),
                    h("p", { class: "faq-text" }, data.event_title)
                ),
                h("main", {}, body)
            )
        );
    } catch (err) {
        showError(err.message);
    }
}
