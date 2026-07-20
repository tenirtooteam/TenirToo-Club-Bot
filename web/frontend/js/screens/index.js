// Файл: web/frontend/js/screens/index.js
// Регистрация маршрутов экранов [feature 015]. main.js вызывает registerScreens(router)
// до старта роутера. Маршрут карточки существует в двух формах: событие (#/event/:id) и
// анонс (#/ann/:id, вход по ?ann_id=). Неизвестный маршрут -> dashboard (fallback).
import * as dashboard from "./dashboard.js";
import * as eventsList from "./events-list.js";
import * as eventCard from "./event-card.js";
import * as eventForm from "./event-form.js";
import * as topics from "./topics.js";
import * as profile from "./profile.js";
import * as admin from "./admin.js";
import * as rolesFaq from "./roles-faq.js";

export function registerScreens(router) {
    router.register("#/dashboard", () => dashboard.render());
    router.register("#/events", () => eventsList.render());
    // Порядок важен: более специфичные маршруты до "#/event/:id" (иначе :id поглотит "new"/"…/edit").
    router.register("#/event/new", () => eventForm.renderCreate());
    router.register("#/event/:id/edit", (p) => eventForm.renderEdit(p.id));
    router.register("#/event/:id", (p) => eventCard.render("event", p.id));
    router.register("#/ann/:id", (p) => eventCard.render("ann", p.id));
    router.register("#/topics", () => topics.render());
    router.register("#/profile", () => profile.render());
    router.register("#/admin/topics", () => admin.renderTopics());
    router.register("#/admin/groups", () => admin.renderGroups());
    router.register("#/roles", () => rolesFaq.render());
    router.setNotFound(() => dashboard.render());
}
