import flatpickr from 'flatpickr';
import htmx from 'htmx.org';
import { getValue, initializeSelect2, initializeSelect2Fields } from './select2.js';

/* What a control says about itself, written by `nautobot/extras/conditions/forms.py` and read back here. */
const ROLE_ATTRIBUTE = 'data-nb-condition-role';
const KEY_ATTRIBUTE = 'data-nb-condition-key';
const CAST_ATTRIBUTE = 'data-nb-condition-cast';
const Role = {
  NEGATE: 'negate',
  PATH: 'path',
  SOURCE: 'source',
  SUBFIELD: 'subfield',
  TYPE: 'type',
  VALUE: 'value',
};
const CAST_BOOLEAN = 'boolean';

/* Written by hand, in `extras/inc/conditions_row.html`. */
const INDEX_ATTRIBUTE = 'data-nb-condition-index';

const CONDITION_CLASS = 'nb-condition';
const REMOVE_BUTTON_CLASS = 'nb-delete-row';

/* On the message the server sends in place of the rows when the stored JSON cannot be read. */
const UNREADABLE_CLASS = 'nb-conditions-unreadable';

/* Dispatched on the list whenever the rows have to be drawn from the field again. */
const RELOAD_EVENT = 'nb-conditions:reload';

/* On the form while the rows are drawn from the field. They show less than it holds, so they must not write back. */
const DRAWING_ATTRIBUTE = 'data-nb-drawing';

/*
 * One past the highest in use, so a row removed from the middle never lends its index to a new one.
 * The add button asks for this through `hx-vals`, reaching it as `window.nb.conditions.nextIndex`.
 */
export const nextIndex = () => {
  const list = document.getElementById('conditions-rows');
  const used = [...(list?.children ?? [])]
    .map((line) => Number(line.getAttribute(INDEX_ATTRIBUTE)))
    .filter(Number.isInteger);
  return used.length ? Math.max(...used) + 1 : 0;
};

/*
 * The conditions of an event rule, edited as rows rather than as raw JSON. The server renders the
 * rows, deciding from the chosen preset, field and operator which controls each one holds. What is
 * here keeps the JSON field synchronized with them, adds and removes rows, and raises the native
 * events select2 leaves unfired.
 */
export const initializeConditionsEditor = () => {
  const field = document.getElementById('id_conditions');
  const list = document.getElementById('conditions-rows');
  const addButton = document.getElementById('conditions-add');
  if (!field || !field.form || !list || !addButton) {
    return;
  }

  const contentTypes = document.getElementById('id_content_types');
  const counter = document.getElementById('conditions-count');

  const setDrawing = (drawing) => field.form.setAttribute(DRAWING_ATTRIBUTE, String(drawing));
  const isDrawing = () => field.form.getAttribute(DRAWING_ATTRIBUTE) === 'true';

  setDrawing(true);

  const controlsWithRole = (line, role) => [...line.querySelectorAll(`[${ROLE_ATTRIBUTE}="${role}"]`)];

  /* What one control contributes to the stored row. Undefined for a boolean left unanswered. */
  const storedValue = (control) => {
    if (control.getAttribute(CAST_ATTRIBUTE) === CAST_BOOLEAN) {
      return control.value === '' ? undefined : control.value === 'True';
    }
    return getValue(control);
  };

  /* A field path is two selects, stored as the two joined by a dot. */
  const storedPath = (line, control) => {
    const key = control.getAttribute(KEY_ATTRIBUTE);
    const sub = line.querySelector(`[${ROLE_ATTRIBUTE}="${Role.SUBFIELD}"][${KEY_ATTRIBUTE}="${key}"]`);
    return [key, sub && sub.value ? `${control.value}.${sub.value}` : control.value];
  };

  const readRow = (line) => {
    const [type] = controlsWithRole(line, Role.TYPE);
    if (!type || !type.value) {
      return null;
    }
    const negate = controlsWithRole(line, Role.NEGATE)[0]?.value === 'not';
    const [source] = controlsWithRole(line, Role.SOURCE);
    if (source) {
      return { negate, source: source.value, type: type.value };
    }
    const values = Object.fromEntries([
      ...controlsWithRole(line, Role.PATH).map((control) => storedPath(line, control)),
      ...controlsWithRole(line, Role.VALUE)
        .map((control) => [control.getAttribute(KEY_ATTRIBUTE), storedValue(control)])
        .filter(([, value]) => value !== undefined),
    ]);
    return { negate, preset: type.value, type: 'preset', values };
  };

  const writeField = () => {
    /*
     * Nothing is written while a message stands in for JSON that could not be read. There are no
     * rows to read, so writing would replace the broken JSON with `[]` and lose the typo with it.
     */
    if (list.querySelector(`.${UNREADABLE_CLASS}`)) {
      return;
    }
    const rows = [...list.children].map((line) => readRow(line)).filter(Boolean);
    field.value = JSON.stringify(rows, null, 4);
  };

  /*
   * What the live region says. A screen reader is told nothing when a row is swapped in or deleted,
   * so it is given the count.
   */
  const announceCount = () => {
    if (!counter) {
      return;
    }
    if (list.querySelector(`.${UNREADABLE_CLASS}`)) {
      counter.textContent = 'Conditions could not be read.';
      return;
    }
    const count = list.querySelectorAll(`.${CONDITION_CLASS}`).length;
    counter.textContent = count === 1 ? '1 condition' : `${count} conditions`;
  };

  const initializeControls = (scope) => {
    /*
     * On the controls rather than on the list, which is not a form control. Rebinding after a swap
     * is free: this already runs for every swap, and the DOM ignores a listener it already holds.
     */
    [...scope.querySelectorAll('input, select, textarea')].forEach((control) =>
      control.addEventListener('input', writeField),
    );
    /* What arrives is plain HTML, so its widgets are set up the way the page sets up its own. */
    initializeSelect2Fields(scope);
    flatpickr(scope.querySelectorAll('.date-picker'), { allowInput: true });
    /*
     * `initializeSelect2Fields` overwrites every placeholder and clear button, so the static selects
     * are set up again from what they declare. Static only, because a second setup would cost the
     * other kinds their swatches, paging or tag input.
     */
    initializeSelect2(scope, 'select.nautobot-select2-static', (element) => ({
      allowClear: Boolean(element.querySelector('option[value=""]')),
      placeholder: element.getAttribute('data-placeholder') ?? '---------',
    }));
  };

  const redrawAll = () => {
    setDrawing(true);
    list.dispatchEvent(new Event(RELOAD_EVENT));
  };

  /*
   * Select2 sets a value through jQuery, which fires no native event. `input` writes the field and
   * `change` is what the control's own `hx-trigger` waits for, so both are raised by hand.
   */
  $(list).on('select2:select select2:unselect select2:clear', 'select', (event) => {
    ['input', 'change'].forEach((name) => event.currentTarget.dispatchEvent(new Event(name)));
  });

  list.addEventListener('click', (event) => {
    const button = event.target.closest(`.${REMOVE_BUTTON_CLASS}`);
    if (button) {
      button.closest(`.${CONDITION_CLASS}`).remove();
      writeField();
      announceCount();
    }
  });

  htmx.onLoad((content) => {
    if (content !== list && !list.contains(content)) {
      return;
    }
    initializeControls(content);
    announceCount();
    if (!isDrawing()) {
      writeField();
    }
  });

  /*
   * The redraw is over once its rows have landed, and they may write to the field again. On a failed
   * request too, because `afterSettle` never comes and the flag would stand for good.
   */
  ['htmx:afterSettle', 'htmx:responseError', 'htmx:sendError', 'htmx:timeout'].forEach((name) =>
    list.addEventListener(name, () => setDrawing(false)),
  );

  /* Whatever was typed or pasted on the JSON tab is what the rows are drawn from. */
  const formTab = document.getElementById('conditions_form-tab');
  if (formTab) {
    formTab.addEventListener('shown.bs.tab', redrawAll);
  }
  if (contentTypes) {
    /* Another object type is another set of fields, so every row is asked for again. */
    $(contentTypes).on('change', redrawAll);
  }
};
