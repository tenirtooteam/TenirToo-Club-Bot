// Файл: web/frontend/js/api.js
// Единая fetch-обёртка веб-моста [feature 015].
//
// Прикрепляет заголовок init-data (идентичность — только из проверенных init-data, R-SEC-1),
// трактует успех СТРУКТУРНО (по полю ответа/статусу, не по подстроке текста) и единообразно
// поднимает ошибки. Разбора дат и бизнес-правил здесь нет — валидация только на сервере (R-SEC-3).

const tg = window.Telegram && window.Telegram.WebApp;

/**
 * Вызов API. Бросает Error(detail) с полями .status и .data при не-2xx.
 * @param {string} url
 * @param {{method?: string, body?: object|null}} [opts]
 */
export async function apiFetch(url, { method = "GET", body = null } = {}) {
    const headers = { "X-TG-Init-Data": (tg && tg.initData) || "" };
    const options = { method, headers };
    if (body != null) {
        headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);

    let data = null;
    try {
        data = await response.json();
    } catch (_) {
        data = null;
    }

    if (!response.ok) {
        const detail = (data && (data.detail || data.message)) || `Ошибка ${response.status}`;
        const error = new Error(detail);
        error.status = response.status;
        error.data = data;
        throw error;
    }
    return data;
}

export const api = {
    get: (url) => apiFetch(url),
    post: (url, body) => apiFetch(url, { method: "POST", body }),
    put: (url, body) => apiFetch(url, { method: "PUT", body }),
    del: (url) => apiFetch(url, { method: "DELETE" }),
};
