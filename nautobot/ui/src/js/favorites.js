import * as bootstrap from 'bootstrap';
import htmx from 'htmx.org';
import { flipAttributes } from './flip.js';

const FAVORITE_ACTIVE_CLASS = 'active';
const FAVORITE_CURRENT_DATA_ATTRIBUTE = 'data-nb-favorite-current';
const FAVORITE_LINK_DATA_ATTRIBUTE = 'data-nb-favorite-link';
const FAVORITE_MODAL_ID = 'nautobot-generic-modal';

/*
 * This React-style ref for `brandingTitle` is set during `initializeFavorites`, and used later by `getFavoriteName`
 * which needs to exist outside the scope of the former, hence the requirement for a shared module-level state for both.
 */
const brandingTitleRef = { current: '' };

/**
 * Get the initial favorite link form field value.
 * @returns {string} Current page URL relative to the origin.
 */
export const getFavoriteLink = () => `${window.location.pathname}${window.location.search}${window.location.hash}`;

/**
 * Get the initial favorite name form field value.
 * @returns {string} Current document title, stripped down from the `brandingTitle` suffix.
 */
export const getFavoriteName = () => {
  const suffix = ` - ${brandingTitleRef.current}`;
  return document.title.endsWith(suffix) ? document.title.slice(0, -suffix.length) : document.title;
};

/**
 * Initialize favorite buttons and add favorite form modal on the page.
 * @param {string} addUrl - `{% url "user:navbar_favorites_add" %}`, needs to be injected from a template.
 * @param {string} deleteUrl - `{% url "user:navbar_favorites_delete" %}`, needs to be injected from a template.
 * @param {string} brandingTitle - `{{ settings.BRANDING_TITLE }}`, needs to be injected from a template.
 * @returns {(function(): void)} Destructor function that reverts favorites initialization.
 */
export const initializeFavorites = (addUrl, deleteUrl, brandingTitle) => {
  brandingTitleRef.current = brandingTitle ?? '';

  // By default, htmx does not swap error responses, but an invalid add form requires exactly that, hence the override.
  const onHtmxBeforeSwap = (event) => {
    const { elt, path } = event.detail.requestConfig;
    if (path === addUrl && event.detail.xhr.status === 400 && elt.closest(`#${FAVORITE_MODAL_ID}`)) {
      event.detail.shouldSwap = true;
    }
  };

  const onHtmxAfterRequest = (event) => {
    const { formData, path } = event.detail.requestConfig;

    // Ignore the request if it was not successful, or was sent to a view other than navbar favorites add or delete.
    if (!event.detail.successful || ![addUrl, deleteUrl].includes(path)) {
      return;
    }

    const link = formData.get('link')?.toLowerCase();
    const buttons = document.querySelectorAll(`[${FAVORITE_LINK_DATA_ATTRIBUTE}="${link}"]`);
    const modal = document.getElementById(FAVORITE_MODAL_ID);
    const shouldBeActive = path === addUrl;

    // Flip attributes of buttons with the favorite `link`. In case of buttons without flip configuration this is a no-op.
    buttons.forEach((button) => {
      if (button.classList.contains(FAVORITE_ACTIVE_CLASS) !== shouldBeActive) {
        flipAttributes(button);
      }
    });

    // Close favorites modal after an add favorite request. In case of a delete favorite request this is a no-op.
    if (modal) {
      bootstrap.Modal.getOrCreateInstance(modal).hide();
    }
  };

  /*
   * `data-nb-favorite-current` marks favorite buttons which should be matched against the current page URL, hence
   * should actively follow any URL changes. For these buttons, this is what needs to happen during synchronization:
   *   1. Update their `data-nb-favorite-link` attribute to the current page URL.
   *   2. Check whether they should change their state, and flip their attributes accordingly.
   * Favorite buttons without the `-current` attribute represent fixed links and are not subject to synchronization.
   */
  const synchronizeFavoriteButtons = () => {
    const link = getFavoriteLink().toLowerCase();
    const favorites = [...document.querySelectorAll('.nb-sidenav-favorites-container li a')];
    const shouldBeActive = favorites.some((favorite) => favorite.getAttribute('href').toLowerCase() === link);
    document.querySelectorAll(`[${FAVORITE_CURRENT_DATA_ATTRIBUTE}]`).forEach((button) => {
      button.setAttribute(FAVORITE_LINK_DATA_ATTRIBUTE, link);
      if (button.classList.contains(FAVORITE_ACTIVE_CLASS) !== shouldBeActive) {
        flipAttributes(button);
      }
    });
  };

  htmx.on('htmx:beforeSwap', onHtmxBeforeSwap);
  htmx.on('htmx:afterRequest', onHtmxAfterRequest);
  htmx.on('htmx:pushedIntoHistory', synchronizeFavoriteButtons);
  window.addEventListener('hashchange', synchronizeFavoriteButtons);
  window.addEventListener('popstate', synchronizeFavoriteButtons);
  window.addEventListener('nb-history:push-state', synchronizeFavoriteButtons);
  window.addEventListener('nb-history:replace-state', synchronizeFavoriteButtons);

  return () => {
    htmx.off('htmx:beforeSwap', onHtmxBeforeSwap);
    htmx.off('htmx:afterRequest', onHtmxAfterRequest);
    htmx.off('htmx:pushedIntoHistory', synchronizeFavoriteButtons);
    window.removeEventListener('hashchange', synchronizeFavoriteButtons);
    window.removeEventListener('popstate', synchronizeFavoriteButtons);
    window.removeEventListener('nb-history:push-state', synchronizeFavoriteButtons);
    window.removeEventListener('nb-history:replace-state', synchronizeFavoriteButtons);
  };
};
