/**
 * Initialize collapse toggle all buttons identified by `data-nb-toggle="collapse-all"` data attribute. Collapse toggle
 * all buttons can be further configured with `data-nb-target="{collapse CSS selector}"` data attribute specifying which
 * collapse elements they control. When not explicitly set, target collapse CSS selector falls back to `".collapse"`.
 * ---
 * Critical difference between this and default Bootstrap 5 collapse implementation is that Bootstrap only supports
 * toggling individual table panel states without an option to toggle them collectively. See an explanation below:
 * Bootstrap 5 on "Collapse All Groups" button click:  |  Nautobot on "Collapse All Groups" button click:
 *   * X [expanded]  -> [collapsed]             |    * X [expanded]  -> [collapsed]
 *   * Y [collapsed] -> [expanded]              |    * Y [collapsed] -> [collapsed]
 *   * Z [expanded]  -> [collapsed]             |    * Z [expanded]  -> [collapsed]
 * ---
 * @returns {function(): void} Destructor function - remove all event listeners added during initialization.
 */

const LOCAL_STORAGE_COLLAPSE_STATE_KEY = 'nautobot.collapseState';
const TABLE_PANEL_KEY_PREFIX = 'collapseme-';
const DEFAULT_STATE = 'expanded';
const GROUP_DEFAULT_STATE_KEY = '__default';

export const initializeCollapseToggleAll = () => {
  // --------------------
  // Helpers
  // --------------------
  const areAll = (collapsableElements, collapsedOrExpanded) =>
    collapsableElements.every((element) => {
      const isCollapsed = !element.classList.contains('show');
      return collapsedOrExpanded === 'collapsed' ? isCollapsed : !isCollapsed;
    });
  const areAllElementsCollapsed = (collapsableElements) => areAll(collapsableElements, 'collapsed');

  const getNautobotTargetQuerySelector = (toggleAllButton) => toggleAllButton.dataset.nbTarget || '.collapse';
  const getAllToggleAllButtons = () => [...document.querySelectorAll('[data-nb-toggle="collapse-all"]')];

  const getAllCollapseElements = (collapseToggleAll) => [
    ...document.querySelectorAll(collapseToggleAll.dataset.nbTarget || '.collapse'),
  ];

  // --------------------
  // Local Storage / Persistence
  // --------------------
  const getTablePanelKeyFromElement = (element) =>
    [...element.classList].find((className) => className.startsWith(TABLE_PANEL_KEY_PREFIX)) || null;
  const getAllTablePanelStatuses = (collapseElements) => {
    const allTablePanelStatuses = new Map();

    collapseElements.forEach((collapseElement) => {
      const tablePanelKey = getTablePanelKeyFromElement(collapseElement);
      if (!tablePanelKey || allTablePanelStatuses.has(tablePanelKey)) {
        return;
      }
      allTablePanelStatuses.set(tablePanelKey, collapseElement.classList.contains('show') ? 'expanded' : 'collapsed');
    });

    return allTablePanelStatuses;
  };

  const updateTableGroupDisplay = (collapseElements) => {
    const allTablePanelStatuses = getAllTablePanelStatuses(collapseElements);
    allTablePanelStatuses.forEach((state, tablePanelKey) => {
      document
        .querySelectorAll(`[data-bs-target=".${tablePanelKey}"]`)
        .forEach((trigger) => trigger.setAttribute('aria-expanded', String(state === 'expanded')));
    });
  };

  const readStoredCollapseState = () => {
    try {
      return JSON.parse(window.localStorage.getItem(LOCAL_STORAGE_COLLAPSE_STATE_KEY)) || {};
    } catch {
      return {};
    }
  };

  const updateToggleAllButtonDisplay = (toggleAllButton) => {
    const tableGroupState = readStoredCollapseState()[getNautobotTargetQuerySelector(toggleAllButton)] || {};
    const currentlyExpandedGroups = Object.values(tableGroupState).some((state) => state === 'expanded');
    const areAnyExpanded =
      currentlyExpandedGroups || areAllElementsCollapsed(getAllCollapseElements(toggleAllButton)) === false;
    toggleAllButton.setAttribute('aria-expanded', String(areAnyExpanded));
    toggleAllButton.textContent = areAnyExpanded ? 'Collapse All Groups' : 'Expand All Groups';
  };

  const writeStoredCollapseState = (container) => {
    try {
      window.localStorage.setItem(LOCAL_STORAGE_COLLAPSE_STATE_KEY, JSON.stringify(container));
    } catch {
      /* Storage unavailable - skip persistence */
    }
  };

  const saveGroupDefaultState = (toggleAllButton, panelState) => {
    const updatedCollapsedState = readStoredCollapseState();
    updatedCollapsedState[getNautobotTargetQuerySelector(toggleAllButton)] = { [GROUP_DEFAULT_STATE_KEY]: panelState };
    writeStoredCollapseState(updatedCollapsedState);
  };

  const saveCollapsedState = () => {
    const updatedCollapsedState = readStoredCollapseState();

    getAllToggleAllButtons().forEach((toggleAllButton) => {
      const nautobotTargetQuerySelector = getNautobotTargetQuerySelector(toggleAllButton);
      const collapseElements = getAllCollapseElements(toggleAllButton);
      const tablePanelStatuses = Object.fromEntries(getAllTablePanelStatuses(collapseElements));

      updatedCollapsedState[nautobotTargetQuerySelector] = {
        ...updatedCollapsedState[nautobotTargetQuerySelector],
        ...tablePanelStatuses,
      };
    });

    writeStoredCollapseState(updatedCollapsedState);
  };

  const getGroupDefaultState = (tableGroupState) => tableGroupState[GROUP_DEFAULT_STATE_KEY] || DEFAULT_STATE;

  const restoreCollapsedState = () => {
    const currentCollapsedState = readStoredCollapseState();

    getAllToggleAllButtons().forEach((toggleAllButton) => {
      const nautobotTargetQuerySelector = getNautobotTargetQuerySelector(toggleAllButton);
      const tableGroupState = currentCollapsedState[nautobotTargetQuerySelector] || {};
      const groupDefaultState = getGroupDefaultState(tableGroupState);

      const collapseElements = getAllCollapseElements(toggleAllButton);
      collapseElements.forEach((collapseElement) => {
        const tablePanelKey = getTablePanelKeyFromElement(collapseElement);
        if (!tablePanelKey) {
          return;
        }

        const panelState = tableGroupState[tablePanelKey] || groupDefaultState;
        collapseElement.classList.toggle('show', panelState === 'expanded');
      });

      updateTableGroupDisplay(collapseElements);
      updateToggleAllButtonDisplay(toggleAllButton);
    });
  };

  // --------------------
  // Event Functions
  // --------------------
  const onClick = (event) => {
    const collapseToggleAll = event.target.closest('[data-nb-toggle="collapse-all"]');

    if (collapseToggleAll) {
      const shouldCollapse = collapseToggleAll.getAttribute('aria-expanded') === 'true';

      saveGroupDefaultState(collapseToggleAll, shouldCollapse ? 'collapsed' : 'expanded');

      getAllCollapseElements(collapseToggleAll).forEach((collapse) => {
        const collapseInstance = window.bootstrap.Collapse.getOrCreateInstance(collapse, { toggle: false });

        if (shouldCollapse) {
          collapseInstance.hide();
        } else {
          collapseInstance.show();
        }
      });

      getAllToggleAllButtons().forEach(updateToggleAllButtonDisplay);
    }
  };

  // Bootstrap - on collapse completed
  const onHiddenBsCollapse = () => {
    saveCollapsedState();
    getAllToggleAllButtons().forEach(updateToggleAllButtonDisplay);
  };

  // Bootstrap - on expand completed
  const onShownBsCollapse = () => {
    saveCollapsedState();
    getAllToggleAllButtons().forEach(updateToggleAllButtonDisplay);
  };

  // Initial page load state restoration
  restoreCollapsedState();

  // --------------------
  // Event Handlers
  // --------------------
  const onHtmxAfterSwap = () => restoreCollapsedState();

  // Using event delegation pattern here to avoid re-creating listeners each time DOM is modified.
  document.addEventListener('click', onClick);
  document.addEventListener('hidden.bs.collapse', onHiddenBsCollapse);
  document.addEventListener('shown.bs.collapse', onShownBsCollapse);
  document.addEventListener('htmx:afterSwap', onHtmxAfterSwap);
  document.addEventListener('htmx:oobAfterSwap', onHtmxAfterSwap);

  return () => {
    document.removeEventListener('click', onClick);
    document.removeEventListener('hidden.bs.collapse', onHiddenBsCollapse);
    document.removeEventListener('shown.bs.collapse', onShownBsCollapse);
    document.removeEventListener('htmx:afterSwap', onHtmxAfterSwap);
    document.removeEventListener('htmx:oobAfterSwap', onHtmxAfterSwap);
  };
};
