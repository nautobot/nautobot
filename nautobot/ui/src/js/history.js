const SESSION_STORAGE_KEY = 'historyState';

/**
 * Load last saved history state from `sessionStorage`.
 *
 * *The idea behind this and `saveState` function below is to be able to maintain history state between history entries
 * separated by a full document reload caused by navigation or form submission. Browsers do not export any native API
 * to manage history state in said scenario, so the workaround is to call `saveState` before full document reload and
 * then `loadState` after the document is loaded back again. `saveState` must be called on demand by arbitrary logic,
 * whereas `loadState` is executed automatically by the main `nautobot.js` script and should not be called manually.*
 *
 * @returns {void} Do not return any value, update current history entry with last saved state instead.
 */
export const loadState = () => {
  const state = (() => {
    try {
      const item = window.sessionStorage?.getItem(SESSION_STORAGE_KEY);
      return item ? JSON.parse(item) : undefined;
      // eslint-disable-next-line no-unused-vars
    } catch (exception) {
      return undefined;
    }
  })();

  if (state !== undefined) {
    const url = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    window.history?.replaceState(state, '', url);
    window.sessionStorage?.removeItem(SESSION_STORAGE_KEY);
  }
};

/**
 * Save given state, or current history entry state if not explicitly passed, into `sessionStorage`.
 *
 * *The idea behind this and `loadState` function above is to be able to maintain history state between history entries
 * separated by a full document reload caused by navigation or form submission. Browsers do not export any native API
 * to manage history state in said scenario, so the workaround is to call `saveState` before full document reload and
 * then `loadState` after the document is loaded back again. `saveState` must be called on demand by arbitrary logic,
 * whereas `loadState` is executed automatically by the main `nautobot.js` script and should not be called manually.*
 *
 * @param {object|null} [state] - Optional `state` object to be saved; current history entry state will be used if
 *   `state` is not explicitly passed. Use `null` to remove history state from `sessionStorage`.
 * @returns {void} Do not return any value, save current history entry state into `sessionStorage` instead.
 */
export const saveState = (state) => {
  const stateToSave = state === undefined ? window.history?.state : state;

  if (stateToSave !== undefined) {
    window.sessionStorage?.setItem(SESSION_STORAGE_KEY, JSON.stringify(stateToSave));
  }
};
