// Файл: web/frontend/js/screens/profile.js
// Экран профиля пользователя [feature 015 US3]: ID, имя, роли.
import { h, mount } from "../render.js";
import { api } from "../api.js";
import { root, showLoading, showError } from "./shell.js";

function roleTag(r) {
    const suffix = r.topic_id ? ` (T:${r.topic_id})` : "";
    return h("span", { class: "role-tag" }, `${r.name}${suffix}`);
}

export async function render() {
    showLoading();
    try {
        const data = await api.get("/api/dashboard/profile");
        mount(root(),
            h("div", { class: "view" },
                h("header", { class: "sub-header" }, h("h2", {}, "👤 Профиль пользователя")),
                h("main", {},
                    h("div", { class: "profile-card" },
                        h("div", { class: "profile-info" },
                            h("label", {}, "Ваш ID"),
                            h("span", {}, String(data.user_id))
                        ),
                        h("div", { class: "profile-info" },
                            h("label", {}, "Имя в системе"),
                            h("span", {}, data.name)
                        ),
                        h("div", { class: "profile-info" },
                            h("label", {}, "Ваши роли"),
                            h("div", { class: "roles-list" }, data.roles.map(roleTag))
                        )
                    )
                )
            )
        );
    } catch (err) {
        showError(err.message);
    }
}
