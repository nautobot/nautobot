const DRAWER_CLASS = 'nb-drawer';
const DRAWER_OPEN_CLASS = 'nb-drawer-open';

/**
 * Toggle drawer element with an option to force open/close.
 * @param {HTMLElement} drawer - Drawer HTML element to be toggled.
 * @param {boolean} [force] - Optionally force opening (`true`) or closing (`false`) regardless of current state.
 * @returns {void} Do not return any value, modify existing HTML element in-place.
 */
const toggleDrawer = (drawer, force) => {
  if (!drawer) {
    return;
  }

  drawer.classList.toggle(DRAWER_OPEN_CLASS, force);

  const isOpen = drawer.classList.contains(DRAWER_OPEN_CLASS);

  drawer.setAttribute('aria-hidden', isOpen ? 'false' : 'true');

  const drawerToggles = [...document.querySelectorAll(`[data-nb-toggle="drawer"][data-nb-target="#${drawer.id}"]`)];
  drawerToggles.forEach((drawerToggle) => drawerToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false'));

  /*
   * Maintain proper element focus when the drawer is:
   *   1. Open - focus the drawer as soon as it becomes visible and focusable.
   *   2. Closed - in case focus is within the drawer move it back to the first found drawer toggle and, if not
   *     available, the `main` element instead.
   */
  if (isOpen) {
    // Close other open drawers if there are any. Effectively, this allows only one drawer to be open at a time.
    const openDrawers = document.getElementsByClassName(DRAWER_OPEN_CLASS);
    [...openDrawers]
      .filter((openDrawer) => openDrawer !== drawer)
      .forEach((openDrawer) => toggleDrawer(openDrawer, false));

    (() => {
      let rafRetriesRemaining = 100; // In case something goes wrong prevent falling into an infinite loop.

      // Use `requestAnimationFrame` to wait until drawer becomes visible and focusable.
      window.requestAnimationFrame(function focusDrawer() {
        const isDrawerVisible = window.getComputedStyle(drawer).visibility === 'visible';

        if (isDrawerVisible) {
          drawer.focus();
        } else if (rafRetriesRemaining > 0) {
          rafRetriesRemaining -= 1;
          window.requestAnimationFrame(focusDrawer);
        }
      });
    })();
  } else if (drawer.contains(document.activeElement)) {
    const nextActiveElement = drawerToggles[0] || document.querySelector('main');
    nextActiveElement?.focus({ preventScroll: true });
  }

  const event = isOpen ? 'nb-drawer:opened' : 'nb-drawer:closed';
  drawer.dispatchEvent(new CustomEvent(event, { bubbles: true, cancelable: true }));
};

/**
 * Initialize custom Nautobot drawers mechanism.
 * @returns {void} Do not return any value, attach an event listener.
 */
export const initializeDrawers = () => {
  // Using event delegation pattern here to avoid re-creating listeners each time DOM is modified.
  document.addEventListener('nb-drawer:close', (event) => toggleDrawer(event.target, false));
  document.addEventListener('nb-drawer:open', (event) => toggleDrawer(event.target, true));
  document.addEventListener('nb-drawer:toggle', (event) => toggleDrawer(event.target));

  document.addEventListener('nb-drawer:opened', (event) => {
    if (event.target.id) {
      const nextState = { ...window.history?.state, drawer: event.target.id };
      const url = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      window.history?.replaceState(nextState, '', url);
    }
  });

  document.addEventListener('nb-drawer:closed', () => {
    // eslint-disable-next-line no-unused-vars
    const { drawer, ...restState } =
      typeof window.history?.state === 'object' && window.history.state !== null ? window.history.state : {};
    const nextState = Object.keys(restState).length > 0 ? restState : null;
    const url = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    window.history?.replaceState(nextState, '', url);
  });

  document.addEventListener('click', (event) => {
    const dismiss = event.target.closest('[data-nb-dismiss]');
    const toggle = event.target.closest('[data-nb-toggle]');

    if (dismiss?.dataset.nbDismiss === 'drawer') {
      const drawer = dismiss.closest(`.${DRAWER_CLASS}`);
      drawer?.dispatchEvent(new CustomEvent(`nb-drawer:close`, { bubbles: true, cancelable: true }));
    } else if (toggle?.dataset.nbToggle === 'drawer') {
      const drawer = document.querySelector(toggle.dataset.nbTarget);
      drawer?.dispatchEvent(new CustomEvent(`nb-drawer:toggle`, { bubbles: true, cancelable: true }));
    }
  });

  if (window.history?.state?.drawer) {
    document
      .getElementById(window.history.state.drawer)
      ?.dispatchEvent(new CustomEvent('nb-drawer:open', { bubbles: true, cancelable: true }));
  }
};
