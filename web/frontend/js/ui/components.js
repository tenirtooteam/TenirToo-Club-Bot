// Файл: web/frontend/js/ui/components.js
// Общие визуальные компоненты дизайн-системы v2 [feature 015 US4].
// Статус кодируется ФОРМОЙ (ведущая точка; квадрат = черновик/модерация), не только цветом
// (доступность/дальтонизм, FR-018). Date-chip показывает диапазон для многодневного похода.
import { h } from "../render.js";

/**
 * Бейдж статуса события. Форма маркера различает состояния независимо от цвета.
 * @param {string} status "approved" | "pending" | иное
 */
export function statusBadge(status) {
    if (status === "approved") {
        return h("span", { class: "event-badge badge ok" }, "Активно");
    }
    if (status === "pending") {
        // square-маркер + предупреждающий цвет — «на модерации/черновик».
        return h("span", { class: "event-badge badge warn square" }, "На модерации");
    }
    return h("span", { class: "event-badge badge mut" }, status || "—");
}

/**
 * Карточка заявки в очереди модерации [feature 016 US1/US4]. Тип кодируется ФОРМОЙ бейджа
 * (ведущая точка = участие; квадрат = черновик), не только цветом (FR-015). Действия — явные
 * Принять/Отклонить. Все строки — текст-нодами (escape-by-default через h/render).
 * @param {{request_id:number,type:string,event_title:string,requester_name:string,created_at:string}} item
 * @param {{onApprove:Function,onReject:Function}} handlers
 */
export function requestCard(item, { onApprove, onReject }) {
    const isParticipation = item.type === "event_participation";
    const badge = isParticipation
        ? h("span", { class: "badge acc" }, "Участие")
        : h("span", { class: "badge warn square" }, "Черновик");

    return h("div", { class: "request-card" },
        h("div", { class: "request-head" },
            badge,
            h("span", { class: "request-time" }, item.created_at)
        ),
        h("h4", { class: "request-title" }, item.event_title),
        h("p", { class: "request-meta" },
            isParticipation ? "Заявитель: " : "Автор: ", item.requester_name),
        h("div", { class: "request-actions" },
            h("button", { class: "btn-approve", onClick: onApprove }, "✓ Принять"),
            h("button", { class: "btn-reject", onClick: onReject }, "✕ Отклонить")
        )
    );
}

/**
 * Чип даты. Для многодневного похода показывает диапазон (start — end) с явным разделителем.
 * Строки — как есть с сервера (презентация, без клиентского разбора дат).
 * @param {string} start
 * @param {string} [end]
 */
export function dateChip(start, end) {
    const s = start || "—";
    if (end && end !== s) {
        return h("span", { class: "date-chip range" },
            s,
            h("span", { class: "rsep" }, "→"),
            end
        );
    }
    return h("span", { class: "date-chip" }, s);
}
