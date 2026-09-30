/*
 * The rows are rendered by the server, which decides from the chosen preset, field and operator which
 * controls each one holds. What is left here is keeping the JSON field in step with the rows, adding
 * and removing them, and handing select2's picks to HTMX, which hears native events only.
 */
document.addEventListener('DOMContentLoaded', () => {
    const field = document.getElementById('id_conditions');
    const list = document.getElementById('conditions-rows');
    const addButton = document.getElementById('conditions-add');
    if (!field || !list || !addButton) {
        return;
    }

    const contentTypes = document.getElementById('id_content_types');
    const ROW_URL = addButton.dataset.rowUrl;

    /*
     * What a rendered control says about itself. `nautobot/extras/conditions/forms.py` writes these,
     * and the two files are one contract: a role renamed on one side only leaves rows written with a
     * piece missing, and nothing complains.
     */
    const ROLE = {
        type: 'type',
        negate: 'negate',
        source: 'source',
        path: 'path',
        subfield: 'subfield',
        value: 'value',
    };
    const CAST_BOOLEAN = 'boolean';

    /* Set on the one row the server sends in place of the table when the JSON cannot be read. */
    const UNREADABLE = 'nb-conditions-unreadable';

    /*
     * True while the rows are being drawn from the field. They must not be written back: a control can
     * only show what it understands, so the round trip would quietly replace what is stored with less.
     */
    let drawing = true;

    const controlIn = (line, role) => line.querySelector(`[data-condition-role="${role}"]`);
    const controlsIn = (line, role) => line.querySelectorAll(`[data-condition-role="${role}"]`);

    /* What one control contributes, or undefined for a boolean nobody has answered. */
    const held = (control) => {
        if (control.multiple) {
            return Array.from(control.selectedOptions, (option) => option.value);
        }
        if (control.dataset.conditionCast === CAST_BOOLEAN) {
            return control.value === '' ? undefined : control.value === 'true';
        }
        return control.value;
    };

    const readRow = (line) => {
        const type = controlIn(line, ROLE.type);
        if (!type || !type.value) {
            return null;
        }
        const negate = controlIn(line, ROLE.negate)?.value === 'not';
        const source = controlIn(line, ROLE.source);
        if (source) {
            return { type: type.value, source: source.value, negate };
        }
        const values = {};
        /* A field path is two selects, and it is stored as the two joined by a dot. */
        controlsIn(line, ROLE.path).forEach((control) => {
            const key = control.dataset.conditionKey;
            const sub = line.querySelector(
                `[data-condition-role="${ROLE.subfield}"][data-condition-key="${key}"]`);
            values[key] = sub && sub.value ? `${control.value}.${sub.value}` : control.value;
        });
        controlsIn(line, ROLE.value).forEach((control) => {
            const value = held(control);
            if (value !== undefined) {
                values[control.dataset.conditionKey] = value;
            }
        });
        return { type: 'preset', preset: type.value, values, negate };
    };

    const writeField = () => {
        /*
         * Not while the table is standing in for a field that could not be read. Every row it shows
         * then reads as nothing, so writing would replace what was typed with `[]`, and the typo that
         * caused it could no longer be found, let alone fixed.
         */
        if (list.querySelector(`.${UNREADABLE}`)) {
            return;
        }
        const rows = Array.from(list.children, (line) => readRow(line)).filter(Boolean);
        field.value = JSON.stringify(rows, null, 4);
    };

    /* One past the highest in use, so a row removed from the middle never lends its index to a new one. */
    const nextIndex = () => {
        const used = Array.from(list.children, (line) => Number(line.dataset.conditionIndex)).filter(
            Number.isInteger);
        return used.length ? Math.max(...used) + 1 : 0;
    };

    const chosenContentTypes = () =>
        (contentTypes ? Array.from(contentTypes.selectedOptions, (option) => option.value) : []).filter(Boolean);

    const dressWidgets = (scope) => {
        /* The same call every dynamic formset here makes after adding a row. */
        jsify_form(scope);
        /*
         * `initializeSelect2Fields` writes `---------` over every placeholder, so a select that names
         * what it is has to be set up again here. The rest of these settings repeat that function's
         * and have to be kept in step with it.
         *
         * Static selects only. Setting one up again replaces whatever it was given the first time, and
         * the other kinds are given things worth keeping: the swatches on a colour picker, searching
         * and paging on an API select, typing your own values on a tag select.
         */
        scope.querySelectorAll('select.nautobot-select2-static[data-placeholder]').forEach((select) => {
            $(select).select2({
                allowClear: true,
                placeholder: select.dataset.placeholder,
                selectionCssClass: 'select2--small',
                theme: 'bootstrap-5',
                width: 'off',
            });
        });
        scope.querySelectorAll('select').forEach((select) => {
            /*
             * Clearing a select2 ends in `trigger('toggle')`, which opens the dropdown and moves focus
             * into it. The dropdown hangs off `<body>` and is positioned after that, so the page scrolls
             * away. Clearing should clear and nothing else.
             */
            $(select).on('select2:clear', () => {
                $(select).one('select2:opening', (event) => {
                    event.preventDefault();
                });
            });
        });
    };

    const redrawAll = () => {
        drawing = true;
        document.body.dispatchEvent(new Event('conditions:reload'));
    };

    /* Select2 announces a pick with a jQuery event only, which nothing listening natively hears. */
    $(list).on('select2:select select2:clear', 'select', (event) => {
        event.currentTarget.dispatchEvent(new Event('change', { bubbles: true }));
    });

    list.addEventListener('change', writeField);
    list.addEventListener('input', writeField);

    list.addEventListener('click', (event) => {
        const button = event.target.closest('.delete-row');
        if (button) {
            button.closest('tr').remove();
            writeField();
        }
    });

    addButton.addEventListener('click', () => {
        htmx.ajax('GET', ROW_URL, {
            target: list,
            swap: 'beforeend',
            values: { index: nextIndex(), content_types: chosenContentTypes() },
        });
    });

    htmx.onLoad((content) => {
        if (content !== list && !list.contains(content)) {
            return;
        }
        dressWidgets(content);
        if (!drawing) {
            writeField();
        }
    });

    /*
     * After every row of a redraw has landed, so the rows are the field's again and may write to it.
     * On a failed request too: `afterSettle` never comes then, and the flag left standing would keep
     * the field from ever being written again.
     */
    ['htmx:afterSettle', 'htmx:responseError', 'htmx:sendError', 'htmx:timeout'].forEach((name) =>
        list.addEventListener(name, () => {
            drawing = false;
        }));

    /* Whatever was typed or pasted on the JSON tab is what the rows are drawn from. */
    const formTab = document.getElementById('conditions_form-tab');
    if (formTab) {
        formTab.addEventListener('shown.bs.tab', redrawAll);
    }
    if (contentTypes) {
        /* Another object type is another set of fields, so every row is asked for again. */
        $(contentTypes).on('change', redrawAll);
    }
});
