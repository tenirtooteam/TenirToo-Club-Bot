// Файл: web/frontend/js/screens/event-card.js
// Карточка события/анонса [feature 015 US3]. Общий рендер для двух контекстов:
//   mode="event" -> /api/dashboard/events/{id}         (toggle: .../toggle)
//   mode="ann"   -> /api/announcements/{id}            (toggle: .../toggle)
// Участие — по ЯВНОМУ намерению из отрисованного состояния кнопки (feature 014): сервер —
// единственный авторитет, устаревшее состояние безопасно (no-op на сервере).
import { h, mount } from "../render.js";
import { api } from "../api.js";
import * as router from "../router.js";
import { root, showLoading, showError } from "./shell.js";

const tg = window.Telegram && window.Telegram.WebApp;

function endpoints(mode, id) {
    if (mode === "ann") {
        return { get: `/api/announcements/${id}`, toggle: `/api/announcements/${id}/toggle` };
    }
    return { get: `/api/dashboard/events/${id}`, toggle: `/api/dashboard/events/${id}/toggle` };
}

function buildCard(mode, id, data, toggleUrl) {
    const btn = h("button", {
        id: "toggle-btn",
        class: data.is_participant ? "action-btn joined" : "action-btn",
    }, h("span", { id: "btn-text" }, data.is_participant ? "Вы участвуете (Отменить)" : "Записаться"));

    btn.addEventListener("click", async () => {
        if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred("medium");
        btn.disabled = true;
        const action = btn.classList.contains("joined") ? "leave" : "join";
        try {
            const result = await api.post(`${toggleUrl}?action=${action}`);
            if (result.success) {
                if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
                render(mode, id); // перерисовываем карточку свежими данными
            } else {
                if (tg) tg.showAlert(result.message);
                btn.disabled = false;
            }
        } catch (err) {
            if (tg) tg.showAlert(err.message || "Произошла ошибка");
            btn.disabled = false;
        }
    });

    // Edit-affordance: только когда сервер подтвердил can_edit (D7/U1); поле есть лишь в
    // event-details DTO (mode="event"), в анонсе его нет — там кнопка не появляется.
    const editBtn = data.can_edit
        ? h("button", {
            class: "edit-btn",
            onClick: () => router.navigate(`#/event/${id}/edit`),
        }, "✏️ Редактировать")
        : null;

    return h("div", { class: "view" },
        h("header", {},
            h("div", { class: "event-badge", id: "event-status" },
                data.status === "approved" ? "Активно" : "На модерации"),
            h("h1", { id: "event-title" }, data.title),
            h("p", { class: "date-range", id: "event-dates" },
                `${data.start_date} — ${data.end_date || "?"}`),
            editBtn
        ),
        h("main", {},
            h("div", { class: "stats-row" },
                h("div", { class: "stat-card" },
                    h("span", { class: "stat-label" }, "Участники"),
                    h("span", { class: "stat-value", id: "participants-count" },
                        String(data.participants_count))
                )
            ),
            h("div", { class: "description-section" },
                h("h3", {}, "Описание"),
                h("p", { id: "event-description" },
                    "Это автоматический анонс мероприятия. Подробности можно уточнить в чате клуба.")
            )
        ),
        h("footer", {}, btn)
    );
}

export async function render(mode, id) {
    showLoading();
    const { get, toggle } = endpoints(mode, id);
    try {
        const data = await api.get(get);
        mount(root(), buildCard(mode, id, data, toggle));
    } catch (err) {
        showError(err.message);
    }
}
