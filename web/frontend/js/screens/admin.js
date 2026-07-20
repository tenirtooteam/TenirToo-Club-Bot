// Файл: web/frontend/js/screens/admin.js
// Админ-экраны [feature 015 US3]: глобальный реестр топиков и шаблоны доступа (группы).
// Серверный гейт (is_global_admin) остаётся на эндпоинтах; здесь только рендер списка.
import { h, mount } from "../render.js";
import { api } from "../api.js";
import { root, showLoading, showError } from "./shell.js";

function listRow(title, subtitle) {
    return h("div", { class: "list-item" },
        h("div", { class: "list-item-content" },
            h("h4", {}, title),
            h("p", {}, subtitle)
        )
    );
}

async function renderList({ url, heading, rowSubtitle, mapRow }) {
    showLoading();
    try {
        const items = await api.get(url);
        const body = h("div", { class: "list-container" }, items.map(mapRow));
        mount(root(),
            h("div", { class: "view" },
                h("header", { class: "sub-header" }, h("h2", {}, heading)),
                h("main", {}, body)
            )
        );
    } catch (err) {
        showError(err.message);
    }
}

export function renderTopics() {
    return renderList({
        url: "/api/dashboard/admin/topics",
        heading: "📍 Глобальный реестр топиков",
        mapRow: (t) => listRow(t.name, `ID: ${t.id} • Глобальный доступ`),
    });
}

export function renderGroups() {
    return renderList({
        url: "/api/dashboard/admin/groups",
        heading: "📂 Шаблоны доступа (Группы)",
        mapRow: (g) => listRow(g.name, "Группа/Шаблон доступа"),
    });
}
