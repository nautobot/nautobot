const ICON_COLLAPSED_CLASS = 'mdi-window-maximize';
const ICON_EXPANDED_CLASS = 'mdi-window-minimize';
const OVERVIEW_ROW_ID_DATA_ATTRIBUTE = 'data-nb-overview-row-id';
const OVERVIEW_TOGGLE_BUTTON_CLASS = 'nb-overview-toggle';

/**
 * Set the toggle button expanded state along with a title, accessible label and icon.
 * @param {HTMLButtonElement} button - Overview toggle button.
 * @param {boolean} isExpanded - Whether the overview row this button controls is currently expanded or not.
 * @returns {void} Do not return any value, modify the given button in-place.
 */
const setToggleButtonState = (button, isExpanded) => {
  const title = button.getAttribute(isExpanded ? 'data-nb-title-expanded' : 'data-nb-title-collapsed');
  button.setAttribute('aria-expanded', String(isExpanded));
  button.setAttribute('title', title);

  const accessibleLabel = button.querySelector('span.visually-hidden');
  accessibleLabel?.replaceChildren(title);

  const icon = button.querySelector('span.mdi');
  icon?.classList.toggle(ICON_COLLAPSED_CLASS, !isExpanded);
  icon?.classList.toggle(ICON_EXPANDED_CLASS, isExpanded);
};

/**
 * Find the overview row controlled by the given toggle button.
 * @param {HTMLButtonElement} button - Overview toggle button.
 * @returns {HTMLTableRowElement|null} Overview row if it is currently in the DOM, `null` otherwise.
 */
const findOverviewRow = (button) => document.getElementById(button.getAttribute(OVERVIEW_ROW_ID_DATA_ATTRIBUTE));

/**
 * Synchronize a toggle button state with the outcome of its htmx request. The row is swapped in by htmx itself, so a
 * missing row means the request failed and the toggle button should stay collapsed.
 * @param {CustomEvent} event - `htmx:afterOnLoad` event, carrying the requesting element in `detail.elt`.
 * @returns {void} Do not return any value, modify the requesting button in-place.
 */
const afterOverviewExpansion = (event) => {
  const button = event.detail?.elt;
  if (!button?.closest(`.${OVERVIEW_TOGGLE_BUTTON_CLASS}`)) {
    return;
  }

  const isExpanded = Boolean(findOverviewRow(button));
  if (isExpanded) {
    button.setAttribute('aria-controls', button.getAttribute(OVERVIEW_ROW_ID_DATA_ATTRIBUTE));
  }
  setToggleButtonState(button, isExpanded);
};

/**
 * Collapse an already expanded overview row.
 * @param {MouseEvent} event - `click` event delegated from the document.
 * @returns {void} Do not return any value, remove the overview row and modify its toggle in-place.
 */
const collapseOverview = (event) => {
  const button = event.target.closest(`.${OVERVIEW_TOGGLE_BUTTON_CLASS}`);
  if (button?.getAttribute('aria-expanded') !== 'true') {
    return;
  }

  findOverviewRow(button)?.remove();
  button.removeAttribute('aria-controls');
  setToggleButtonState(button, false);
};

/**
 * Initialize expandable overview rows for every table rendering overview toggles. Expansion is handled by the toggle
 * button htmx attributes, and these listeners serve two purposes: keeping the button in sync and handling collapsing.
 * @returns {function(): void} Destructor function - remove all event listeners added during initialization.
 */
export const initializeOverviews = () => {
  document.addEventListener('htmx:afterOnLoad', afterOverviewExpansion);
  document.addEventListener('click', collapseOverview);

  return () => {
    document.removeEventListener('htmx:afterOnLoad', afterOverviewExpansion);
    document.removeEventListener('click', collapseOverview);
  };
};
