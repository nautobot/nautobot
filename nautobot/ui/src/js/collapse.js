/**
 * Collapse.js powers every "Collapse All / Expand All" button in the UI (Jobs list, Custom/Computed Fields
 * panels). It's initialized once globally on page load.
 *
 * The entry point is a button with data-nb-toggle="collapse-all" and data-nb-target="<selector>", which
 * tells it which .collapse elements to control. Each group is identified by its collapseme-* class.
 *
 * State lives in localStorage (nautobot.collapsedState) as a namespaced dictionary — keyed per button's
 * target selector — storing each group's "expanded"/"collapsed" plus a __default for groups not yet seen.
 *
 * The collapse-all action runs in onClick. Everything else — saving group state and refreshing the button
 * label + chevrons — is batched into a single requestAnimationFrame so localStorage is written once per
 * repaint. `OnLoad`` and after HTMX swaps trigger restoreCollapsedState replays the stored state back onto the DOM.
 * ---
 * Collapse toggle all buttons can be further configured with `data-nb-target="{collapse CSS selector}"`
 * data attribute specifying which collapse elements they control. When not explicitly set, target
 * collapse CSS selector falls back to `".collapse"`.
 * ---
 * Critical difference between this and default Bootstrap 5 collapse implementation is that Bootstrap only supports
 * toggling individual table panel states without an option to toggle them collectively. See an explanation below:
 * Bootstrap 5 on "Collapse All Groups" button click:  |  Nautobot on "Collapse All Groups" button click:
 *   * X [expanded]  -> [collapsed]             |    * X [expanded]  -> [collapsed]
 *   * Y [collapsed] -> [expanded]              |    * Y [collapsed] -> [collapsed]
 *   * Z [expanded]  -> [collapsed]             |    * Z [expanded]  -> [collapsed]
 * ---
 * Local Storage Representation will look like this
 * {
 *   "nautobot.collapsedState": {
 *     "#job_accordion .collapse": {
 *       "__default": "expanded",
 *       "collapseme-custom-field-system-jobs": "expanded",
 *       "collapseme-custom-field-system-jobs2": "expanded",
 *       "collapseme-example-app-jobs": "expanded",
 *       "collapseme-system-jobs": "expanded"
 *     },
 *     "[class^=\"collapseme-custom_fields_False-\"]": {
 *       "__default": "expanded",
 *       "collapseme-custom_fields_False-1": "expanded",
 *       "collapseme-custom_fields_False-2": "expanded"
 *     },
 *     "[class^=\"collapseme-computed_fields_False-\"]": {
 *       "__default": "expanded",
 *       "collapseme-computed_fields_False-1": "expanded",
 *       "collapseme-computed_fields_False-2": "expanded"
 *     }
 *   }
 * }
 * ---
 * @returns {function(): void} Destructor function - remove all event listeners added during initialization.
 */

const LOCAL_STORAGE_COLLAPSE_STATE_KEY = 'nautobot.collapsedState';
const TABLE_PANEL_KEY_PREFIX = 'collapseme-';
const TABLE_PANEL_DEFAULT_STATE_KEY = '__default';

export const initializeCollapseToggleAll = () => {
  // --------------------
  // Runtime State
  // --------------------
  // Used to help schedule saving and syncing
  let isSaveStateAndSyncViewScheduled = false;

  // --------------------
  // Helpers
  // --------------------
  const areAll = (collapsableElements, collapsedOrExpanded) =>
    collapsableElements.every((collapsableElement) => {
      const isCollapsed = !collapsableElement.classList.contains('show');
      return collapsedOrExpanded === 'collapsed' ? isCollapsed : !isCollapsed;
    });
  const areAllElementsCollapsed = (collapsableElements) => areAll(collapsableElements, 'collapsed');
  const areAllElementsExpanded = (collapsableElements) => areAll(collapsableElements, 'expanded');

  const getToggleAllButtonTargetQuerySelector = (toggleAllButton) => toggleAllButton.dataset.nbTarget || '.collapse';
  const getAllToggleAllButtonElements = () => [...document.querySelectorAll('[data-nb-toggle="collapse-all"]')];

  const getAllCollapsableElementsFromToggleAllButton = (toggleAllButton) => [
    ...document.querySelectorAll(toggleAllButton.dataset.nbTarget || '.collapse'),
  ];

  const getTablePanelKey = (collapsableElement) =>
    [...collapsableElement.classList].find((className) => className.startsWith(TABLE_PANEL_KEY_PREFIX)) || null;

  // --------------------
  // Local Storage / Persistence
  // --------------------
  const readLocalStorageCollapsedState = () => {
    try {
      return JSON.parse(window.localStorage.getItem(LOCAL_STORAGE_COLLAPSE_STATE_KEY)) || {};
    } catch {
      return {};
    }
  };

  const writeLocalStorageCollapsedState = (newState) => {
    try {
      window.localStorage.setItem(LOCAL_STORAGE_COLLAPSE_STATE_KEY, JSON.stringify(newState));
    } catch {
      /* Storage unavailable - skip persistence */
    }
  };

  // Collapse All and Expand All are global actions, so they discard every per-group override and let the new default govern every group, including groups on pages that are not currently rendered.
  const resetLocalStorageCollapsedStateNamespaceToDefault = (collapsedStateNamespaceKey, newDefaultState) => {
    const localStorageCollapsedState = readLocalStorageCollapsedState();

    localStorageCollapsedState[collapsedStateNamespaceKey] = { [TABLE_PANEL_DEFAULT_STATE_KEY]: newDefaultState };

    writeLocalStorageCollapsedState(localStorageCollapsedState);
  };

  const saveState = () => {
    const localStorageCollapsedState = readLocalStorageCollapsedState();

    getAllToggleAllButtonElements().forEach((toggleAllButtonElement) => {
      const collapsedStateNamespaceKey = getToggleAllButtonTargetQuerySelector(toggleAllButtonElement);
      const tablePanelCollapsedState = { ...(localStorageCollapsedState[collapsedStateNamespaceKey] || {}) };

      getAllCollapsableElementsFromToggleAllButton(toggleAllButtonElement).forEach((collapsableElement) => {
        const tablePanelKey = getTablePanelKey(collapsableElement);
        if (!tablePanelKey) {
          return;
        }
        tablePanelCollapsedState[tablePanelKey] = collapsableElement.classList.contains('show')
          ? 'expanded'
          : 'collapsed';
      });

      localStorageCollapsedState[collapsedStateNamespaceKey] = tablePanelCollapsedState;
    });

    writeLocalStorageCollapsedState(localStorageCollapsedState);
  };

  // --------------------
  // View
  // --------------------
  // The button label flips only at the extremes: "Expand All Groups" once every group is collapsed, "Collapse All Groups" once every group is expanded. In a mixed state the label is left unchanged so it keeps whichever action it was last offering.
  const syncView = () => {
    getAllToggleAllButtonElements().forEach((toggleAllButtonElement) => {
      const allCollapsableElements = getAllCollapsableElementsFromToggleAllButton(toggleAllButtonElement);

      // Nothing to reflect until the collapse elements exist (they can be swapped in later by htmx); an empty set would otherwise read as "all collapsed" and wrongly flip the label.
      if (allCollapsableElements.length === 0) {
        return;
      }

      if (areAllElementsCollapsed(allCollapsableElements)) {
        toggleAllButtonElement.setAttribute('aria-expanded', 'false');
        toggleAllButtonElement.textContent = 'Expand All Groups';
      } else if (areAllElementsExpanded(allCollapsableElements)) {
        toggleAllButtonElement.setAttribute('aria-expanded', 'true');
        toggleAllButtonElement.textContent = 'Collapse All Groups';
      }
    });
  };

  const restoreCollapsedState = () => {
    const localStorageCollapsedState = readLocalStorageCollapsedState();

    getAllToggleAllButtonElements().forEach((toggleAllButtonElement) => {
      const collapsedStateNamespaceKey = getToggleAllButtonTargetQuerySelector(toggleAllButtonElement);
      const namespaceCollapsedState = localStorageCollapsedState[collapsedStateNamespaceKey] || {};
      const namespaceDefaultState = namespaceCollapsedState[TABLE_PANEL_DEFAULT_STATE_KEY] || 'expanded';

      getAllCollapsableElementsFromToggleAllButton(toggleAllButtonElement).forEach((collapsableElement) => {
        const tablePanelKey = getTablePanelKey(collapsableElement);
        const tablePanelState = tablePanelKey
          ? namespaceCollapsedState[tablePanelKey] || namespaceDefaultState
          : namespaceDefaultState;
        const isExpanded = tablePanelState === 'expanded';

        collapsableElement.classList.toggle('show', isExpanded);

        if (tablePanelKey) {
          document.querySelectorAll(`[data-bs-target=".${tablePanelKey}"]`).forEach((groupToggleButton) => {
            groupToggleButton.setAttribute('aria-expanded', String(isExpanded));
          });
        }
      });
    });

    syncView();
  };

  // --------------------
  // Events
  // --------------------
  // When called it sets the `isSaveStateAndSyncViewScheduled` and schedules logic to run in the next scheduled repaint.
  const scheduleSaveStateAndSyncView = () => {
    if (isSaveStateAndSyncViewScheduled === true) {
      return;
    }

    isSaveStateAndSyncViewScheduled = true;

    window.requestAnimationFrame(() => {
      if (isSaveStateAndSyncViewScheduled === true) {
        isSaveStateAndSyncViewScheduled = false;
        saveState();
        syncView();
      }
    });
  };

  // Triggers toggling, but doesn't change state. State update occurs in the events fired on the end of the bootstrap collapse/expand animation.
  const onClick = (event) => {
    const toggleAllButtonElement = event.target.closest('[data-nb-toggle="collapse-all"]');
    if (!toggleAllButtonElement) {
      return;
    }

    const collapsedStateNamespace = getToggleAllButtonTargetQuerySelector(toggleAllButtonElement);
    const allCollapsableElements = getAllCollapsableElementsFromToggleAllButton(toggleAllButtonElement);
    // Act on whichever action the button is currently offering, so the click always matches the visible label.
    const shouldExpandEveryGroup = toggleAllButtonElement.getAttribute('aria-expanded') !== 'true';

    const namespaceDefaultState = shouldExpandEveryGroup === true ? 'expanded' : 'collapsed';
    resetLocalStorageCollapsedStateNamespaceToDefault(collapsedStateNamespace, namespaceDefaultState);

    allCollapsableElements.forEach((collapsableElement) => {
      const bootstrapCollapseInstance = window.bootstrap.Collapse.getOrCreateInstance(collapsableElement, {
        toggle: false,
      });
      if (shouldExpandEveryGroup) {
        bootstrapCollapseInstance.show();
      } else {
        bootstrapCollapseInstance.hide();
      }
    });

    // Bootstrap only fires collapse/expand events for elements that actually change, so schedule a save and sync directly to cover clicks where every rendered group is already in the target state.
    scheduleSaveStateAndSyncView();
  };

  const onBootstrapExpandFinish = () => {
    scheduleSaveStateAndSyncView();
  };

  const onBootstrapCollapseFinish = () => {
    scheduleSaveStateAndSyncView();
  };

  const onHtmxAfterSwap = () => restoreCollapsedState();

  // --------------------
  // Event Handlers
  // --------------------
  // Using event delegation pattern here to avoid re-creating listeners each time DOM is modified.
  restoreCollapsedState();

  document.addEventListener('click', onClick);
  document.addEventListener('hidden.bs.collapse', onBootstrapCollapseFinish);
  document.addEventListener('shown.bs.collapse', onBootstrapExpandFinish);
  document.addEventListener('htmx:afterSwap', onHtmxAfterSwap);
  document.addEventListener('htmx:oobAfterSwap', onHtmxAfterSwap);

  return () => {
    document.removeEventListener('click', onClick);
    document.removeEventListener('hidden.bs.collapse', onBootstrapCollapseFinish);
    document.removeEventListener('shown.bs.collapse', onBootstrapExpandFinish);
    document.removeEventListener('htmx:afterSwap', onHtmxAfterSwap);
    document.removeEventListener('htmx:oobAfterSwap', onHtmxAfterSwap);
  };
};
