// Файл: web/frontend/js/screens/moderation-queue.js
// Экран очереди модерации [feature 016 US1/US2/US4].
//
// Скоупленная под зрителя очередь (сервер решает, что показать): глобальный админ — черновики,
// организатор — заявки на участие своих походов. Действия Принять/Отклонить -> resolve; успех
// структурный (по полю ответа). Устаревший элемент («уже обработана») — мягкий алерт + перерисовка.
import { h, mount } from "../render.js";
import { api } from "../api.js";
import { requestCard } from "../ui/components.js";
import { root, showLoading, showError } from "./shell.js";

const tg = window.Telegram && window.Telegram.WebApp;

async function resolve(requestId, status) {
    if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred("medium");
    try {
        const result = await api.post(`/api/moderation/requests/${requestId}/resolve`, { status });
        if (result.success) {
            if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
        } else if (tg) {
            tg.showAlert(result.message); // устаревший элемент: заявка уже обработана
        }
    } catch (err) {
        if (tg) tg.showAlert(err.message || "Произошла ошибка");
    }
    render(); // всегда перерисовываем свежей очередью (устаревшие элементы уходят)
}

export async function render() {
    showLoading();
    try {
        const data = await api.get("/api/moderation/queue");
        const items = data.items || [];
        const body = items.length === 0
            ? h("div", { class: "empty-state" }, "Заявок на модерацию нет.")
            : h("div", { class: "list-container" },
                items.map((it) => requestCard(it, {
                    onApprove: () => resolve(it.request_id, "approved"),
                    onReject: () => resolve(it.request_id, "rejected"),
                })));
        mount(root(),
            h("div", { class: "view" },
                h("header", { class: "sub-header" }, h("h2", {}, "🛡️ Модерация")),
                h("main", {}, body)
            )
        );
    } catch (err) {
        showError(err.message);
    }
}
