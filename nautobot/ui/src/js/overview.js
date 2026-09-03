const ICON_COLLAPSED_CLASS = 'mdi-window-maximize';
const ICON_EXPANDED_CLASS = 'mdi-window-minimize';
const OVERVIEW_ROW_ID_DATA_ATTRIBUTE = 'data-nb-overview-row-id';
const OVERVIEW_TOGGLE_BUTTON_CLASS = 'nb-overview-toggle';

const setToggleState = (toggle, isExpanded) => {
  const title = toggle.getAttribute(isExpanded ? 'data-nb-title-expanded' : 'data-nb-title-collapsed');
  toggle.setAttribute('aria-expanded', String(isExpanded));
  toggle.setAttribute('title', title);

  const accessibleLabel = toggle.querySelector('span.visually-hidden');
  accessibleLabel?.replaceChildren(title);

  const icon = toggle.querySelector('span.mdi');
  icon?.classList.toggle(ICON_COLLAPSED_CLASS, !isExpanded);
  icon?.classList.toggle(ICON_EXPANDED_CLASS, isExpanded);
};

const findOverviewRow = (toggle) => document.getElementById(toggle.getAttribute(OVERVIEW_ROW_ID_DATA_ATTRIBUTE));

const afterOverviewExpansion = (event) => {
  const toggle = event.detail?.elt;
  if (!toggle?.closest(`.${OVERVIEW_TOGGLE_BUTTON_CLASS}`)) {
    return;
  }
  if (findOverviewRow(toggle)) {
    toggle.setAttribute('aria-controls', toggle.getAttribute(OVERVIEW_ROW_ID_DATA_ATTRIBUTE));
  }
  setToggleState(toggle, true);
};

const collapseOverview = (event) => {
  const toggle = event.target.closest(`.${OVERVIEW_TOGGLE_BUTTON_CLASS}`);
  if (toggle?.getAttribute('aria-expanded') !== 'true') {
    return;
  }
  findOverviewRow(toggle)?.remove();
  toggle.removeAttribute('aria-controls');
  setToggleState(toggle, false);
};

export const initializeOverviews = () => {
  document.body.addEventListener('htmx:afterOnLoad', afterOverviewExpansion);
  document.body.addEventListener('click', collapseOverview);
};
