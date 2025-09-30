import { getCookie, removeCookie, setCookie } from './cookie.js';

const SIDENAV_COLLAPSED_KEY = 'sidenav_collapsed';

/**
 * Expand/collapse sidenav.
 * @returns {void} Do not return any value, modify existing HTML elements, cookies and localStorage in-place.
 */
export const toggleSidenav = () => {
  const toggler = document.querySelector('.nb-sidenav-toggler');

  const controls = toggler.getAttribute('aria-controls');
  const expanded = toggler.getAttribute('aria-expanded') === 'true';

  toggler.setAttribute('aria-expanded', String(!expanded));

  const sidenav = document.getElementById(controls);
  sidenav.classList.toggle('nb-sidenav-collapsed', expanded);

  if (expanded) {
    setCookie(SIDENAV_COLLAPSED_KEY, 'true');
    window.localStorage?.setItem(SIDENAV_COLLAPSED_KEY, 'true');
  } else {
    removeCookie(SIDENAV_COLLAPSED_KEY);
    window.localStorage?.removeItem(SIDENAV_COLLAPSED_KEY);
  }
};

/**
 * Initialize sidenav mechanisms, i.e. expand/collapse, fly-outs, and optionally version control branch picker.
 * @returns {void} Do not return any value, attach event listeners.
 */
export const initializeSidenav = () => {
  const toggler = document.querySelector('.nb-sidenav-toggler');

  if (toggler) {
    /*
     * Check if sidenav expanded/collapsed initial state is valid. If not, amend it by calling `toggleSidenav()`. This
     * should not happen due to template code properly handling the initial render, but we're being extra careful here.
     */
    const sidenavCollapsedInitialState =
      getCookie(SIDENAV_COLLAPSED_KEY) ?? window.localStorage?.getItem(SIDENAV_COLLAPSED_KEY) ?? 'false';
    const shouldToggleSidenav =
      (sidenavCollapsedInitialState === 'true' && toggler.getAttribute('aria-expanded') === 'true') ||
      (sidenavCollapsedInitialState === 'false' && toggler.getAttribute('aria-expanded') === 'false');
    if (shouldToggleSidenav) {
      toggleSidenav();
    }

    toggler.addEventListener('click', toggleSidenav);
  }

  [...document.querySelectorAll('.nb-sidenav-list-item:not(.nb-flat)')].forEach((sidenavListItem) => {
    sidenavListItem.addEventListener('click', () => {
      const controls = sidenavListItem.getAttribute('aria-controls');
      const expanded = sidenavListItem.getAttribute('aria-expanded') === 'true';

      sidenavListItem.setAttribute('aria-expanded', String(!expanded));

      const onClickDocument = (documentClickEvent) => {
        const { target: documentClickTarget } = documentClickEvent;
        const sidenavFlyout = document.getElementById(controls);

        const isClickOutside =
          !sidenavListItem.contains(documentClickTarget) && !sidenavFlyout.contains(documentClickTarget);

        if (isClickOutside) {
          sidenavListItem.setAttribute('aria-expanded', 'false');
          document.removeEventListener('click', onClickDocument);
        }
      };

      if (expanded) {
        document.removeEventListener('click', onClickDocument);
      } else {
        document.addEventListener('click', onClickDocument);
      }
    });
  });

  const sidenavBranchPickerSelect = $('#sidenav-branch-picker-select');
  sidenavBranchPickerSelect.on('change', (event) => event.currentTarget.form.submit());
  sidenavBranchPickerSelect.on('select2:open', () => {
    document.querySelector('.select2-dropdown').setAttribute('data-bs-theme', 'dark');
    document.querySelector('.select2-dropdown .select2-search__field').setAttribute('placeholder', 'Find a branch...');
  });
};
