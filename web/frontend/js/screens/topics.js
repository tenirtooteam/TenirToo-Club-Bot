// Файл: web/frontend/js/screens/topics.js
// Экран доступных топиков [feature 015 US3].
import { h, mount } from "../render.js";
import { api } from "../api.js";
import { root, showLoading, showError } from "./shell.js";

function topicRow(t) {
    return h("div", { class: "list-item" },
        h("div", { class: "list-item-content" },
            h("h4", {}, t.name),
            h("p", {}, `ID: ${t.id}`)
        ),
        h("div", { class: "list-item-arrow" }, "→")
    );
}

export async function render() {
    showLoading();
    try {
        const topics = await api.get("/api/dashboard/topics");
        const body = topics.length === 0
            ? h("div", { class: "empty-state" }, "У вас пока нет доступа к топикам.")
            : h("div", { class: "list-container" }, topics.map(topicRow));
        mount(root(),
            h("div", { class: "view" },
                h("header", { class: "sub-header" }, h("h2", {}, "📍 Доступные топики")),
                h("main", {}, body)
            )
        );
    } catch (err) {
        showError(err.message);
    }
}
