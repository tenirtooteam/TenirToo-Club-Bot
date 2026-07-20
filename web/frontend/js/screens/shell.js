// Файл: web/frontend/js/screens/shell.js
// Общий каркас экранов [feature 015]: корневой контейнер, лоадер, экран ошибки.
import { h, mount } from "../render.js";

export function root() {
    return document.getElementById("app");
}

/** Показывает спиннер на весь экран (во время загрузки данных). */
export function showLoading() {
    mount(root(), h("div", { class: "loader" }, h("div", { class: "spinner" })));
}

/** Показывает экран ошибки (сообщение — текст-нодой, escape-by-default). */
export function showError(message) {
    mount(
        root(),
        h("div", { id: "error-screen" },
            h("div", { class: "error-icon" }, "🏔"),
            h("h2", { id: "error-title" }, "Упс!"),
            h("p", { id: "error-msg" }, message || "Не удалось загрузить данные.")
        )
    );
}
