import flatpickr from 'flatpickr';
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
 * Position a flyout menu near its trigger nav item, centered on the item's midpoint.
 * Clamps to viewport bounds so the flyout never overflows above or below the screen.
 * @param {HTMLElement} listItem - The clicked nav item element.
 * @param {HTMLElement} flyout - The flyout menu element.
 * @returns {void} Do not return any value, modify flyout inline styles in-place.
 */
const positionFlyout = (listItem, flyout) => {
  // Reset position so we can measure the flyout's natural content height
  flyout.style.top = '0px';

  // Wait one frame for layout to calculate the flyout's rendered height
  requestAnimationFrame(() => {
    const itemRect = listItem.getBoundingClientRect();
    const flyoutHeight = flyout.scrollHeight;
    const viewportHeight = window.innerHeight;

    // The flyout is position:absolute inside #sidenav (position:fixed, top:0).
    // Calculate the offset between #sidenav's top and the viewport top
    // So we can convert viewport coordinates to the flyout's coordinate space.
    const parentRect = flyout.offsetParent ? flyout.offsetParent.getBoundingClientRect() : { top: 0 };
    const offset = parentRect.top;

    // Center the flyout on the clicked item's midpoint (in viewport coords)
    const itemMid = itemRect.top + listItem.offsetHeight / 2;
    let top = itemMid - flyoutHeight / 2;

    // Clamp to viewport bounds
    if (top + flyoutHeight > viewportHeight) {
      top = viewportHeight - flyoutHeight;
    }
    if (top < 0) {
      top = 0;
    }

    // Convert from viewport coordinates to the flyout's offset parent coordinates
    flyout.style.top = `${top - offset}px`;
  });
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

  [...document.querySelectorAll('.nb-sidenav-list-item:not(.nb-sidenav-list-item-flat)')].forEach((sidenavListItem) => {
    sidenavListItem.addEventListener('click', () => {
      const controls = sidenavListItem.getAttribute('aria-controls');
      const expanded = sidenavListItem.getAttribute('aria-expanded') === 'true';

      sidenavListItem.setAttribute('aria-expanded', String(!expanded));

      if (!expanded) {
        const sidenavFlyout = document.getElementById(controls);
        positionFlyout(sidenavListItem, sidenavFlyout);
      }

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

  const sidenavBranchPickerReturnUrl = document.querySelector('#sidenav-branch-picker-return-url');
  if (sidenavBranchPickerReturnUrl) {
    // Remove any existing version-control query params from the return URL as they would override the form action
    const return_url = new URL(sidenavBranchPickerReturnUrl.value);
    return_url.searchParams.delete('branch');
    return_url.searchParams.delete('version_control_time_travel_date');
    sidenavBranchPickerReturnUrl.value = return_url.toString();
  }

  const sidenavBranchPickerSelect = $('#sidenav-branch-picker-select');
  sidenavBranchPickerSelect.on('change', (event) => event.currentTarget.form.submit());
  sidenavBranchPickerSelect.on('select2:open', () => {
    document.querySelector('.select2-dropdown').setAttribute('data-bs-theme', 'dark');
    document.querySelector('.select2-dropdown .select2-search__field').setAttribute('placeholder', 'Find a branch...');
  });

  const sidenavTimeTravelReturnUrl = document.querySelector('#sidenav-timetravel-return-url');
  if (sidenavTimeTravelReturnUrl) {
    // Remove any existing version-control query params from the return URL as they would override the form action
    const return_url = new URL(sidenavTimeTravelReturnUrl.value);
    return_url.searchParams.delete('branch');
    return_url.searchParams.delete('version_control_time_travel_date');
    sidenavTimeTravelReturnUrl.value = return_url.toString();
  }

  const sidenavTimeTravelPickerInput = document.querySelector('#sidenav-timetravel-picker');
  if (sidenavTimeTravelPickerInput) {
    flatpickr(sidenavTimeTravelPickerInput, {
      allowInput: true,
      maxDate: 'today',
      onChange: (_selectedDates, dateStr, instance) => {
        instance.input.blur();
        document.querySelector('#timetravel-cancel').classList.toggle('d-none', !dateStr);
        instance.input.form.submit();
      },
      onReady: (_selectedDates, dateStr) => {
        document.querySelector('#timetravel-cancel').classList.toggle('d-none', !dateStr);
      },
      wrap: true,
    });
  }
};
