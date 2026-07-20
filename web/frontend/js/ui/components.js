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
