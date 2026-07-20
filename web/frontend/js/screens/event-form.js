// Файл: web/frontend/js/screens/event-form.js
// Форма авторинга события [feature 015 US1/US2]: create и edit в одном экране.
//
// Клиент отправляет СЫРЫЕ человекочитаемые строки — разбор дат и валидация только на сервере
// (R-CODE-5, R-SEC-3). Здесь лишь UX-подсказки. При отклонении сервером поля формы сохраняются
// (FR-006): показываем ошибку, форму НЕ перерисовываем. Право на edit-экран отражает серверный
// can_edit (D7), но настоящий гейт — на PUT (403 -> вежливый отказ).
import { h, mount } from "../render.js";
import { api } from "../api.js";
import * as router from "../router.js";
import { root, showLoading, showError } from "./shell.js";

const tg = window.Telegram && window.Telegram.WebApp;

function buildForm({ heading, submitLabel, seed, onSubmit }) {
    const titleInput = h("input", {
        type: "text", class: "form-input", placeholder: "Название похода", value: seed.title || "",
    });
    const dateInput = h("input", {
        type: "text", class: "form-input", placeholder: "Когда? (напр. 10-15 июня)", value: seed.dateText || "",
    });
    const endInput = h("input", {
        type: "text", class: "form-input", placeholder: "Дата окончания (необязательно)", value: seed.endDateText || "",
    });
    const errorBox = h("div", { class: "form-error" });
    const submit = h("button", { class: "action-btn" }, submitLabel);

    submit.addEventListener("click", async () => {
        mount(errorBox); // очистить прошлую ошибку
        submit.disabled = true;
        const payload = {
            title: titleInput.value,
            date_text: dateInput.value,
            end_date_text: endInput.value ? endInput.value : null,
        };
        try {
            await onSubmit(payload); // при успехе — навигация внутри
        } catch (err) {
            // FR-006: форма не перерисовывается, введённые значения остаются в полях.
            mount(errorBox, err.message || "Не удалось сохранить.");
            submit.disabled = false;
        }
    });

    return h("div", { class: "view" },
        h("header", { class: "sub-header" }, h("h2", {}, heading)),
        h("main", {},
            h("div", { class: "form-card" },
                h("label", { class: "form-label" }, "Название"),
                titleInput,
                h("label", { class: "form-label" }, "Когда"),
                dateInput,
                h("p", { class: "form-hint" }, "Примеры: 15 мая, завтра, 10-15 июня"),
                h("label", { class: "form-label" }, "Дата окончания (необязательно)"),
                endInput,
                errorBox
            )
        ),
        h("footer", {}, submit)
    );
}

async function afterSave(result) {
    // UX-подсказка про календарь — по серверному признаку, без клиентской логики дат (FR-004).
    if (result && result.date_recognized === false && tg) {
        tg.showAlert("Дату не удалось распознать — поход не попадёт в календарь автоматически.");
    }
    router.navigate(`#/event/${result.event_id}`);
}

export function renderCreate() {
    mount(root(), buildForm({
        heading: "🏔 Новый поход",
        submitLabel: "Создать",
        seed: {},
        onSubmit: async (payload) => afterSave(await api.post("/api/events", payload)),
    }));
}

export async function renderEdit(id) {
    showLoading();
    try {
        const data = await api.get(`/api/dashboard/events/${id}`);
        mount(root(), buildForm({
            heading: "✏️ Редактировать поход",
            submitLabel: "Сохранить",
            seed: { title: data.title, dateText: data.start_date, endDateText: data.end_date || "" },
            onSubmit: async (payload) => afterSave(await api.put(`/api/events/${id}`, payload)),
        }));
    } catch (err) {
        showError(err.message);
    }
}
