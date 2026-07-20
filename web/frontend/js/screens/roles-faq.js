// Файл: web/frontend/js/screens/roles-faq.js
// Справочник ролей [feature 015 US3].
//
// ЕДИНСТВЕННОЕ санкционированное исключение из escape-by-default (FR-013): текст FAQ приходит
// из HelpService.get_help("roles") — это РАЗРАБОТЧЕСКИЙ статический HTML (services/help_service.py),
// НЕ пользовательский ввод, и намеренно содержит форматирующие теги. Пользователь не может его
// отравить, поэтому он рендерится как доверенная разметка. Любые ПОЛЬЗОВАТЕЛЬСКИЕ строки
// (названия, имена) по-прежнему идут только через render.js text-ноды. Тех-долг: при появлении
// структурированного FAQ-контракта заменить на безопасный рендер (D-редизайн).
import { h, mount } from "../render.js";
import { api } from "../api.js";
import { root, showLoading, showError } from "./shell.js";

export async function render() {
    showLoading();
    try {
        const data = await api.get("/api/dashboard/roles/faq");
        const faq = h("div", { class: "faq-text" });
        faq.innerHTML = data.text; // ТОЛЬКО доверенный HelpService-HTML (см. шапку файла)
        mount(root(),
            h("div", { class: "view" },
                h("header", { class: "sub-header" }, h("h2", {}, "🛡️ Справочник ролей")),
                h("main", {}, h("div", { class: "roles-faq-container" }, faq))
            )
        );
    } catch (err) {
        showError(err.message);
    }
}
