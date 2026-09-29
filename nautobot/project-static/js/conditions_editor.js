/*
 * The rows are built in the DOM rather than from a string, so a preset label or help text contributed
 * by an App cannot inject markup.
 *
 * A row is identified by the object it holds rather than by its position, so changing or removing one
 * touches only its own `<tr>` and leaves the rest of the table, and whatever the browser was focused on,
 * where they were.
 */
document.addEventListener('DOMContentLoaded', () => {
    const catalog = document.getElementById('condition-presets');
    const field = document.getElementById('id_conditions');
    const list = document.getElementById('conditions-rows');
    const addButton = document.getElementById('conditions-add');
    if (!catalog || !field || !list || !addButton) {
        return;
    }

    const presets = JSON.parse(catalog.textContent);
    const byKey = Object.fromEntries(presets.map((preset) => [preset.preset, preset]));
    const operators = Object.fromEntries(
        JSON.parse(document.getElementById('condition-operators').textContent).map((operator) => {
            return [operator.key, operator];
        })
    );
    const EXPRESSION = 'expression';
    const FIELD_KIND = 'model_field';
    const VALUE_KIND = 'value';
    const colors = JSON.parse(document.getElementById('condition-colors').textContent);
    const contentTypes = document.getElementById('id_content_types');
    const FIELDS_URL = list.dataset.fieldsUrl;

    let rows = [];
    let fields = [];
    /* Answers can arrive out of order, so only the newest request is allowed to land. */
    let pending = 0;
    let nextId = 0;

    const readField = () => {
        try {
            const parsed = JSON.parse(field.value.trim() || '[]');
            return Array.isArray(parsed) ? parsed : null;
        } catch (error) {
            return null;
        }
    };

    const writeField = () => {
        field.value = JSON.stringify(rows.filter((row) => row.type), null, 4);
    };

    const element = (tag, className, text) => {
        const node = document.createElement(tag);
        if (className) {
            node.className = className;
        }
        if (text) {
            node.textContent = text;
        }
        return node;
    };

    /* Keeps the row's identity, so the `<tr>` it belongs to can still be found. */
    const replaceContents = (row, next) => {
        Object.keys(row).forEach((key) => { delete row[key]; });
        Object.assign(row, next);
    };

    const textInput = (placeholder, value, onInput) => {
        const input = element('input', 'form-control');
        input.type = 'text';
        input.placeholder = placeholder;
        input.value = value === undefined || value === null ? '' : value;
        input.addEventListener('input', () => {
            onInput(input.value);
            writeField();
        });
        return input;
    };

    const typeSelect = (row) => {
        const select = element('select', 'form-select w-auto nautobot-select2-static');
        select.appendChild(element('option', null, ''));
        presets.forEach((preset) => {
            const option = element('option', null, preset.label);
            option.value = preset.preset;
            select.appendChild(option);
        });
        const raw = element('option', null, 'Raw expression');
        raw.value = EXPRESSION;
        select.appendChild(raw);
        select.value = row.type === EXPRESSION ? EXPRESSION : row.preset || '';
        /* select2 fires its change through jQuery, which a native listener does not hear. */
        $(select).on('change', () => {
            if (!select.value) {
                replaceContents(row, {});
            } else if (select.value === EXPRESSION) {
                replaceContents(row, { type: EXPRESSION, source: '', negate: row.negate === true });
            } else {
                replaceContents(row, { type: 'preset', preset: select.value, values: {}, negate: row.negate === true });
            }
            writeField();
            redrawRow(row);
        });
        return select;
    };

    const valueInputs = (row) => {
        if (!row.type) {
            return [];
        }
        if (row.type === EXPRESSION) {
            return [textInput('Jinja2 expression', row.source, (value) => {
                row.source = value;
            })];
        }
        const preset = byKey[row.preset];
        if (!preset) {
            const missing = element('span', 'text-danger align-self-center');
            missing.textContent = 'Preset `' + row.preset + '` is not installed. Remove the row, or install the App that provides it.';
            return [missing];
        }
        if (!row.values) {
            row.values = {};
        }
        const target = chosenTarget(row, preset);
        return preset.parameters.flatMap((parameter) => {
            if (parameter.kind === FIELD_KIND) {
                return fieldInputs(row, parameter);
            }
            if (parameter.choices) {
                return choiceInput(row, parameter, target.kind);
            }
            if (parameter.kind === VALUE_KIND) {
                return valueInput(row, parameter, target);
            }
            const input = textInput(parameter.label, row.values[parameter.name], (value) => {
                row.values[parameter.name] = value;
            });
            input.title = parameter.help_text || '';
            return input;
        });
    };

    /* Everything the value widget is chosen by: what is being compared, and how the operator takes it. */
    const chosenTarget = (row, preset) => {
        const operator = chosenOperator(row, preset);
        const named = namedField(row, preset);
        return {
            ...named,
            /* `contains` and its neighbours match a fragment, so the values that exist are no help. */
            whole: !operator || operator.whole_value,
            many: Boolean(operator && named.kind && operator.set_kinds.includes(named.kind)),
        };
    };

    /*
     * The field this row names: the kind of value it holds, and for a sub-field of a relation, where
     * the objects on the other side can be read and under which key.
     */
    const namedField = (row, preset) => {
        const parameter = preset.parameters.find((candidate) => candidate.kind === FIELD_KIND);
        if (!parameter) {
            return {};
        }
        const stored = (row.values || {})[parameter.name] || '';
        const dot = stored.indexOf('.');
        const top = fields.find((available) => {
            return available.name === (dot === -1 ? stored : stored.slice(0, dot));
        });
        if (!top) {
            return {};
        }
        if (dot === -1) {
            return { kind: top.kind || null, widget: top.widget };
        }
        const sub = (top.subfields || []).find((available) => {
            return available.name === stored.slice(dot + 1);
        });
        if (!sub) {
            return {};
        }
        return { kind: sub.kind || null, url: top.values_url, key: sub.name, widget: sub.widget };
    };

    /* The operator this row compares with, as the operator table describes it. */
    const chosenOperator = (row, preset) => {
        const parameter = preset.parameters.find((candidate) => candidate.choices);
        return parameter ? operators[(row.values || {})[parameter.name]] : undefined;
    };

    const storedValues = (row, parameter) => {
        const stored = row.values[parameter.name];
        if (stored === undefined || stored === null || stored === '') {
            return [];
        }
        return Array.isArray(stored) ? stored : [stored];
    };

    const seedOptions = (select, values) => {
        /* An AJAX or tag select shows nothing for a value it has not been told about. */
        values.forEach((value) => {
            const option = element('option', null, value);
            option.value = value;
            option.selected = true;
            select.appendChild(option);
        });
    };

    const writeOnChange = (select, row, parameter, many) => {
        $(select).on('change', () => {
            row.values[parameter.name] = many ? $(select).val() || [] : select.value;
            writeField();
        });
    };

    const apiSelect = (row, parameter, target) => {
        /*
         * Nautobot's own API-backed select, so searching and paging come with it. `value-field` makes
         * the option's value the same key the condition compares, rather than the object's id.
         */
        const select = element('select', 'form-select nautobot-select2-api');
        select.dataset.url = target.url;
        select.setAttribute('value-field', target.key);
        select.setAttribute('display-field', target.key);
        select.title = parameter.help_text || '';
        select.multiple = target.many;
        seedOptions(select, storedValues(row, parameter));
        writeOnChange(select, row, parameter, target.many);
        return select;
    };

    const colorSelect = (row, parameter, many) => {
        /* The picker every other color field in Nautobot uses, so the swatches match. */
        const select = element('select', 'form-select nautobot-select2-color-picker');
        select.title = parameter.help_text || '';
        select.multiple = many;
        select.appendChild(element('option', null, ''));
        const chosen = storedValues(row, parameter);
        colors.forEach((color) => {
            const option = element('option', null, color.label);
            option.value = color.value;
            option.setAttribute('style', color.style);
            option.selected = chosen.includes(color.value);
            select.appendChild(option);
        });
        writeOnChange(select, row, parameter, many);
        return select;
    };

    const tagsInput = (row, parameter) => {
        /* Nautobot's own type-your-own-values select, used wherever a field takes a set of strings. */
        const select = element('select', 'form-select nautobot-select2-multi-value-char');
        select.title = parameter.help_text || '';
        select.multiple = true;
        seedOptions(select, storedValues(row, parameter));
        writeOnChange(select, row, parameter, true);
        return select;
    };

    const booleanSelect = (row, parameter) => {
        /* `_equals` compares a boolean field only against a real boolean, never against 'true'. */
        const select = element('select', 'form-select');
        select.dataset.placeholder = parameter.label;
        select.title = parameter.help_text || '';
        select.appendChild(element('option', null, ''));
        const stored = row.values[parameter.name];
        const choices = [{ value: 'true', label: 'true' }, { value: 'false', label: 'false' }];
        optionList(select, choices, typeof stored === 'boolean' ? String(stored) : '');
        $(select).on('change', () => {
            if (select.value) {
                row.values[parameter.name] = select.value === 'true';
            } else {
                delete row.values[parameter.name];
            }
            writeField();
        });
        return select;
    };

    const valueInput = (row, parameter, target) => {
        if (target.widget === 'color' && target.whole) {
            return colorSelect(row, parameter, target.many);
        }
        if (target.url && target.key && target.whole) {
            return apiSelect(row, parameter, target);
        }
        if (target.many) {
            return tagsInput(row, parameter);
        }
        if (target.kind === 'boolean') {
            return booleanSelect(row, parameter);
        }
        const kind = target.kind;
        const input = textInput(parameter.label, row.values[parameter.name], (value) => {
            row.values[parameter.name] = value;
        });
        input.title = parameter.help_text || '';
        if (kind === 'number') {
            input.type = 'number';
        }
        if (kind === 'date') {
            /* A record holds a full timestamp, so a bare date orders correctly but never equals one. */
            input.classList.add('date-picker');
            input.placeholder = 'YYYY-MM-DD';
        }
        return input;
    };

    const optionList = (select, choices, chosen) => {
        choices.forEach((choice) => {
            const option = element('option', null, choice.label);
            option.value = choice.value;
            select.appendChild(option);
        });
        /* A stored value the list no longer offers is still shown, rather than silently lost. */
        if (chosen && !choices.some((choice) => choice.value === chosen)) {
            const option = element('option', null, chosen);
            option.value = chosen;
            select.appendChild(option);
        }
        select.value = chosen || '';
    };

    const namedChoices = (entries) => {
        return entries.map((entry) => ({ value: entry.name, label: entry.name }));
    };

    const choiceInput = (row, parameter, kind) => {
        const select = element('select', 'form-select');
        select.dataset.placeholder = parameter.label;
        select.title = parameter.help_text || '';
        select.appendChild(element('option', null, ''));
        /* An operator the table does not describe suits everything, and an unknown kind narrows nothing. */
        const usable = parameter.choices.filter((choice) => {
            const described = operators[choice.value];
            return !kind || !described || described.kinds.includes(kind);
        });
        optionList(select, usable, row.values[parameter.name] || '');
        $(select).on('change', () => {
            row.values[parameter.name] = select.value;
            writeField();
            /* The operator decides whether the value is typed or picked, so the row is drawn again. */
            redrawRow(row);
        });
        return select;
    };

    const fieldInputs = (row, parameter) => {
        const stored = row.values[parameter.name] || '';
        const dot = stored.indexOf('.');
        const chosen = dot === -1 ? stored : stored.slice(0, dot);
        const chosenSub = dot === -1 ? '' : stored.slice(dot + 1);

        if (!fields.length) {
            const waiting = element('select', 'form-select nautobot-select2-static');
            waiting.title = parameter.help_text || '';
            waiting.disabled = true;
            waiting.appendChild(element('option', null, 'Select object type(s) first'));
            return [waiting];
        }
        const select = element('select', 'form-select');
        select.title = parameter.help_text || '';
        select.dataset.placeholder = parameter.label;
        select.appendChild(element('option', null, ''));
        optionList(select, namedChoices(fields), chosen);

        const subfields = (fields.find((available) => available.name === chosen) || {}).subfields || [];
        const inputs = [select];
        if (subfields.length) {
            const subSelect = element('select', 'form-select');
            subSelect.dataset.placeholder = 'Sub-field';
            subSelect.appendChild(element('option', null, ''));
            optionList(subSelect, namedChoices(subfields), chosenSub);
            $(subSelect).on('change', () => {
                row.values[parameter.name] = subSelect.value ? chosen + '.' + subSelect.value : chosen;
                writeField();
                /* A sub-field of another kind needs another widget for the value. */
                redrawRow(row);
            });
            inputs.push(subSelect);
        }

        $(select).on('change', () => {
            row.values[parameter.name] = select.value;
            writeField();
            redrawRow(row);
        });
        return inputs;
    };

    const loadFields = () => {
        const chosen = contentTypes ? Array.from(contentTypes.selectedOptions, (o) => o.value) : [];
        const query = chosen.filter(Boolean).map((id) => 'content-type-id=' + encodeURIComponent(id));
        if (!query.length) {
            fields = [];
            render();
            return;
        }
        const token = ++pending;
        fetch(FIELDS_URL + '?' + query.join('&'), { headers: { Accept: 'application/json' } })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(FIELDS_URL + ' answered ' + response.status);
                }
                return response.json();
            })
            .then((data) => {
                if (token === pending) {
                    fields = data.fields || [];
                    render();
                }
            })
            /* Left visible: swallowing this leaves a disabled picker with nothing saying why. */
            .catch((error) => { console.error('Conditions: could not load the field list.', error); });
    };

    const negateBox = (row) => {
        const wrapper = element('div', 'form-check');
        const input = element('input', 'form-check-input');
        input.type = 'checkbox';
        input.id = 'conditions-negate-' + (nextId += 1);
        input.checked = row.negate === true;
        input.addEventListener('change', () => {
            row.negate = input.checked;
            writeField();
        });
        const label = element('label', 'form-check-label', 'not');
        label.htmlFor = input.id;
        wrapper.appendChild(input);
        wrapper.appendChild(label);
        return wrapper;
    };

    /* The rows and the table's children are built together and stay in the same order. */
    const rowElement = (row) => {
        return list.children[rows.indexOf(row)];
    };

    const removeButton = (row) => {
        const button = element('button', 'btn btn-danger delete-row');
        button.type = 'button';
        button.title = 'Remove this condition';
        button.appendChild(element('span', 'mdi mdi-trash-can-outline'));
        button.addEventListener('click', () => {
            rowElement(row).remove();
            rows.splice(rows.indexOf(row), 1);
            writeField();
        });
        return button;
    };

    const buildRow = (row) => {
        const line = element('tr');
        const type = element('td');
        type.appendChild(typeSelect(row));
        const values = element('td');
        const inputs = element('div', 'nb-condition-values');
        valueInputs(row).forEach((input) => {
            inputs.appendChild(input);
        });
        values.appendChild(inputs);
        const negate = element('td', 'text-nowrap');
        negate.appendChild(negateBox(row));
        const remove = element('td', 'text-end');
        remove.appendChild(removeButton(row));
        line.append(type, values, negate, remove);
        return line;
    };

    const dressWidgets = (scope) => {
        /* The same call every dynamic formset here makes after adding a row. */
        jsify_form(scope);
        /*
         * `initializeSelect2Fields` writes `---------` over every placeholder, so a select that names
         * what it is has to be set up again here. The rest of these settings repeat that function's
         * and have to be kept in step with it.
         */
        scope.querySelectorAll('select[data-placeholder]').forEach((select) => {
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

    const redrawRow = (row) => {
        /*
         * After the event that asked for it, not during. select2 carries on working with the element
         * once its `change` handlers return, and it cannot position a widget already torn out of the
         * document, so it falls back to the top of the page and takes the scroll position with it.
         */
        setTimeout(() => {
            const line = rowElement(row);
            if (line) {
                const replacement = buildRow(row);
                line.replaceWith(replacement);
                dressWidgets(replacement);
            }
        }, 0);
    };

    const render = () => {
        list.replaceChildren();
        if (rows === null) {
            const line = element('tr');
            const cell = element('td', 'text-danger');
            cell.colSpan = 4;
            cell.textContent = 'The JSON tab holds something that is not a list of conditions, so the rows cannot be shown.';
            line.appendChild(cell);
            list.appendChild(line);
            return;
        }
        rows.forEach((row) => {
            list.appendChild(buildRow(row));
        });
        dressWidgets(list);
    };

    const reload = () => {
        rows = readField();
        /* A form with nothing on it still offers one row, the way the other repeating forms here do. */
        if (rows !== null && rows.length === 0) {
            rows.push({});
        }
        render();
    };

    addButton.addEventListener('click', () => {
        if (rows === null) {
            return;
        }
        const row = {};
        rows.push(row);
        const line = buildRow(row);
        list.appendChild(line);
        dressWidgets(line);
    });

    /* Whatever was typed or pasted on the JSON tab is what the rows are rebuilt from. */
    const formTab = document.querySelector('a[href="#conditions_form"]');
    if (formTab) {
        formTab.addEventListener('shown.bs.tab', reload);
    }
    if (contentTypes) {
        $(contentTypes).on('change', loadFields);
    }
    reload();
    loadFields();
});
