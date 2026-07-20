// Файл: web/frontend/js/render.js
// Escape-by-default рендер-слой [feature 015, FR-013].
//
// ЕДИНСТВЕННЫЙ санкционированный путь от данных к DOM. Любая строка попадает в DOM только
// текст-нодой (textContent), поэтому встроенная разметка НЕ исполняется. Сырого innerHTML
// для серверных/пользовательских данных здесь нет и быть не должно: tg.initData живёт в
// том же JS-scope, и невэскейпленный заголовок = кража сессии (R-SEC-1).

/**
 * Создаёт DOM-элемент. Текстовые дети всегда становятся текст-нодами (escape-by-default).
 * @param {string} tag
 * @param {object} [props] class | dataset | on<Event> | обычные атрибуты
 * @param {...(Node|string|number|null|Array)} children
 */
export function h(tag, props = {}, ...children) {
    const el = document.createElement(tag);
    for (const [key, value] of Object.entries(props || {})) {
        if (value == null) continue;
        if (key === "class") {
            el.className = value;
        } else if (key === "dataset") {
            Object.assign(el.dataset, value);
        } else if (key.startsWith("on") && typeof value === "function") {
            el.addEventListener(key.slice(2).toLowerCase(), value);
        } else {
            el.setAttribute(key, value);
        }
    }
    appendChildren(el, children);
    return el;
}

/** Текст-нода из значения (null/undefined -> пустая строка). */
export function text(value) {
    return document.createTextNode(value == null ? "" : String(value));
}

/** Заменяет содержимое узла переданными детьми (безопасно; без innerHTML). */
export function mount(node, ...children) {
    node.replaceChildren();
    appendChildren(node, children);
    return node;
}

/** Очищает узел. */
export function clear(node) {
    node.replaceChildren();
}

function appendChildren(el, children) {
    for (const child of children.flat()) {
        if (child == null) continue;
        el.appendChild(child instanceof Node ? child : text(child));
    }
}
