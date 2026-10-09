import { Tooltip } from 'bootstrap';
import htmx from 'htmx.org';

/*
 * Client-side behavior of the export field picker, the tree of checkboxes that `ExportFieldSelect` renders for the
 * `Export Object List` Job's "Fields to Export". Relationships are read from DOM nesting rather than from the `__`
 * structure of the values, so a `cf_<key>` nested under `custom_fields` behaves like any other nested row.
 */

// Ids that `ExportFieldSelect` gives the picker's own elements; keep these in step with its `*_ID` constants.
const WRAPPER_ID = 'nb-export-fields-picker';
const OMITTED_ID = 'nb-export-fields-omitted';
const SUMMARY_ID = 'nb-export-fields-summary';
// The sibling field naming the content type whose fields are offered; `ExportFieldSelect.content_type_selector`.
const CONTENT_TYPE_SELECTOR = '#id_content_type';

const LIST_SELECTOR = '.nb-export-field-select';
const PARENT_SELECTOR = 'input.nb-export-field-parent';
const LEAF_SELECTOR = 'input.nb-export-field-leaf';

// A parent row's own checkbox is in its header; the fields it stands for are everything nested under it.
const leavesUnder = (row) => [...row.querySelectorAll(`:scope > .nb-export-nested ${LEAF_SELECTOR}`)];

// The option submitting a row's bare path -- "Natural key", say -- is the first row nested directly under it.
const bareOptionOf = (row) => row.querySelector(':scope > .nb-export-nested > li > div input.nb-export-field-bare');

// The rows selecting a related object's natural key, if it has one.
const naturalKeyOf = (parent) => new Set(JSON.parse(parent.getAttribute('data-nb-natural-key') || '[]'));

/*
 * What clicking a parent row does next: which of the rows under it to check, and a tooltip saying so. From nothing:
 * its natural key, or else its bare-path option, if it has either. From everything: nothing. From anything else:
 * everything.
 */
const nextStep = (row, parent, leaves) => {
  const checked = leaves.filter((leaf) => leaf.checked).length;
  if (checked > 0 && checked === leaves.length) {
    return { select: () => false, title: 'Clear these fields' };
  }
  const naturalKey = naturalKeyOf(parent);
  if (checked === 0 && naturalKey.size > 0) {
    return { select: (leaf) => naturalKey.has(leaf.value), title: 'Select the fields that identify this object' };
  }
  const bare = bareOptionOf(row);
  if (checked === 0 && bare) {
    return { select: (leaf) => leaf === bare, title: `Select "${bare.getAttribute('data-nb-label')}"` };
  }
  return { select: () => true, title: 'Select all fields' };
};

// Above the tree, say what the export will contain: the default columns, or how much is selected.
const refreshSummary = (picker, selected) => {
  const clear = picker.querySelector('.nb-export-fields-clear');
  if (clear) {
    clear.disabled = selected === 0;
  }
  const summary = picker.querySelector(`#${SUMMARY_ID}`);
  if (!summary) {
    return;
  }
  summary.querySelector('.nb-export-fields-summary-default').classList.toggle('invisible', selected > 0);
  summary.querySelector('.nb-export-fields-summary-selected').classList.toggle('invisible', selected === 0);
  summary.querySelector('.nb-export-fields-summary-count').textContent = String(selected);
  // Rewritten only on a change, as any write to a live region may be announced.
  const status = summary.querySelector('.nb-export-fields-summary-status');
  const statusText = selected > 0 ? `${selected} selected` : 'No fields selected';
  if (status.textContent !== statusText) {
    status.textContent = statusText;
  }
};

/*
 * Bring each parent row's checkbox into line with what is checked under it: checked when all of it is, indeterminate
 * when some of it is, with a count to say how much while it is collapsed. Then the summary above the tree.
 */
const refresh = (list) => {
  list.querySelectorAll(PARENT_SELECTOR).forEach((parent) => {
    const row = parent.closest('li');
    const leaves = leavesUnder(row);
    const checked = leaves.filter((leaf) => leaf.checked).length;
    parent.checked = checked > 0 && checked === leaves.length;
    parent.indeterminate = checked > 0 && checked < leaves.length;
    const count = row.querySelector(':scope > div > .nb-export-field-count');
    if (count) {
      count.textContent = checked > 0 ? `${checked} of ${leaves.length} selected` : '';
    }
    parent.title = nextStep(row, parent, leaves).title;
  });
  const picker = list.closest(`#${WRAPPER_ID}`);
  if (picker) {
    refreshSummary(picker, list.querySelectorAll(`${LEAF_SELECTOR}:checked`).length);
  }
};

const setExpanded = (row, expanded) => {
  const nested = row.querySelector(':scope > .nb-export-nested');
  const caret = row.querySelector(':scope > div > .nb-export-field-caret');
  if (!nested || !caret) {
    return;
  }
  nested.classList.toggle('d-none', !expanded);
  caret.setAttribute('aria-expanded', String(expanded));
  const icon = caret.querySelector('.mdi');
  if (icon) {
    icon.classList.toggle('mdi-chevron-down', !expanded);
    icon.classList.toggle('mdi-chevron-up', expanded);
  }
};

const onChange = (event) => {
  const changed = event.target;
  const list = changed.closest(LIST_SELECTOR);
  if (!list || !changed.matches('input[type="checkbox"]')) {
    return;
  }
  if (changed.matches(PARENT_SELECTOR)) {
    /*
     * The browser's own toggle of the box is ignored: what is under it is stepped on, and `refresh()` then sets the
     * box to match. The row stays collapsed; its count shows what it now holds.
     */
    const row = changed.closest('li');
    const leaves = leavesUnder(row);
    const { select } = nextStep(row, changed, leaves);
    leaves.forEach((leaf) => {
      leaf.checked = select(leaf);
    });
  }
  refresh(list);
};

const onClear = (clear) => {
  const picker = clear.closest(`#${WRAPPER_ID}`);
  const list = picker?.querySelector(LIST_SELECTOR);
  if (!list) {
    return;
  }
  // Unchecking in script raises no "change" event, so refresh here.
  list.querySelectorAll(LEAF_SELECTOR).forEach((leaf) => {
    leaf.checked = false;
  });
  // The report of what "Match the list view" left out belongs to the selection being cleared.
  picker.querySelector(`#${OMITTED_ID}`)?.remove();
  refresh(list);
};

const onClick = (event) => {
  const clear = event.target.closest('.nb-export-fields-clear');
  if (clear) {
    onClear(clear);
    return;
  }
  // Collapse/expand a parent's nested rows, at any depth.
  const caret = event.target.closest('.nb-export-field-caret');
  if (caret) {
    setExpanded(caret.closest('li'), caret.getAttribute('aria-expanded') !== 'true');
  }
};

export const initializeExportFields = () => {
  document.addEventListener('change', onChange);
  document.addEventListener('click', onClick);

  /*
   * Select2 announces a pick with a jQuery event only, which HTMX never sees
   * (https://github.com/select2/select2/issues/1908). Re-dispatch it as a native `change`, so the picker's
   * `hx-trigger` rebuilds it for the chosen content type. Only where there is a picker: jQuery handlers hear native
   * events too, so elsewhere (Import Objects, say) each pick would be handled twice.
   */
  $(document).on('select2:select select2:clear', CONTENT_TYPE_SELECTOR, (event) => {
    if (document.getElementById(WRAPPER_ID)) {
      event.currentTarget.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });

  /*
   * Whenever a picker is loaded, bring its parent rows and summary into line with what it has checked, and set up its
   * tooltips: the page's own setup only covers what is there when the page first loads, not what HTMX brings in.
   */
  htmx.onLoad((content) => {
    content.querySelectorAll(LIST_SELECTOR).forEach((list) => {
      refresh(list);
      list.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((element) => Tooltip.getOrCreateInstance(element));
    });
  });
  // And dispose of them as HTMX removes the picker, or one showing at the time would be left on the page.
  document.addEventListener('htmx:beforeCleanupElement', (event) => {
    Tooltip.getInstance(event.target)?.dispose();
  });
};
