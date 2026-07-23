// Файл: web/frontend/js/screens/dashboard.js
// Экран дашборда [feature 015 US3]: приветствие, статы, меню-грид (admin-пункты условно).
import { h, mount } from "../render.js";
import { api } from "../api.js";
import * as router from "../router.js";
import { root, showLoading, showError } from "./shell.js";

const tg = window.Telegram && window.Telegram.WebApp;

function menuItem(icon, label, hint, hash) {
    return h("div", {
        class: "menu-item",
        onClick: () => {
            if (tg && tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
            router.navigate(hash);
        },
    },
        h("div", { class: "menu-icon" }, icon),
        h("span", { class: "menu-label" }, label),
        hint != null ? h("span", { class: "menu-hint" }, String(hint)) : null
    );
}

export async function render() {
    showLoading();
    try {
        const data = await api.get("/api/dashboard/init");
        const grid = h("div", { class: "menu-grid" },
            menuItem("📍", "Мои топики", data.stats.topics_available, "#/topics"),
            menuItem("🏔", "Походы", data.stats.events_active, "#/events"),
            menuItem("👤", "Мой профиль", null, "#/profile"),
            menuItem("⚖️", "Модерация", null, "#/moderation"),
            data.is_admin ? menuItem("📍", "Все топики", null, "#/admin/topics") : null,
            data.is_admin ? menuItem("📂", "Шаблоны", null, "#/admin/groups") : null,
            menuItem("🛡️", "Роли", null, "#/roles")
        );
        mount(root(),
            h("div", { class: "view" },
                h("header", {},
                    h("div", { class: "user-profile-summary" },
                        h("div", { class: "avatar-placeholder", id: "user-avatar" }, "🏔"),
                        h("div", { class: "user-text" },
                            h("h1", { id: "user-name" }, `Привет, ${data.name}!`),
                            h("p", { id: "user-status" }, "Ваше центральное варево")
                        )
                    )
                ),
                h("main", {}, grid)
            )
        );
    } catch (err) {
        showError(err.message);
    }
}
