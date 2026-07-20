// Файл: web/frontend/js/main.js
// Bootstrap Mini App [feature 015, FR-014].
//
// Telegram SDK glue, вход по ?ann_id= (карточка анонса, иначе dashboard), регистрация
// экранов и старт роутера. Живые web_app-кнопки под уже разосланными анонсами указывают на
// {WEBAPP_URL}/?ann_id={id} — этот вход обязан вести на нужную карточку (иначе анонсы осиротеют).

import * as router from "./router.js";
import { registerScreens } from "./screens/index.js";

const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
    tg.ready();
    tg.expand();
}

// Все экраны регистрируют свои маршруты до старта роутера.
registerScreens(router);

// Вход по ?ann_id=: маппим query-параметр на маршрут карточки анонса при первичной загрузке.
const annId = new URLSearchParams(location.search).get("ann_id");
if (!location.hash) {
    location.hash = annId ? `#/ann/${encodeURIComponent(annId)}` : "#/dashboard";
}

router.start("#/dashboard");
