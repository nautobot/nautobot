import { getCookie, removeCookie, setCookie } from './cookie.js';

const THEME_MODAL_ID = 'theme_modal';

const THEME_DARK = 'dark';
const THEME_LIGHT = 'light';
const THEME_SYSTEM = 'system';

/**
 * Get preferred system color scheme.
 * @returns {('dark'|'light')} Preferred system color scheme.
 */
const getPreferredColorScheme = () =>
  window.matchMedia?.(`(prefers-color-scheme: ${THEME_DARK})`).matches ? THEME_DARK : THEME_LIGHT;

/**
 * Check if given `theme` is a valid Nautobot theme, i.e. `'dark'`, `'light'`, or `'system'`.
 * @param {string} theme - Theme in question.
 * @returns {boolean} `true` is given `theme` is a valid Nautobot theme, `false` otherwise.
 */
const isValidTheme = (theme) => theme === THEME_DARK || theme === THEME_LIGHT || theme === THEME_SYSTEM;

/**
 * Automatically detect Nautobot theme. It is derived from `cookie` or `localStorage` if set manually, and falls back to
 * preferred system color scheme by default.
 * @returns {('dark'|'light'|'system')} Detected Nautobot theme.
 */
const detectTheme = () => {
  const cookieTheme = getCookie('theme');
  if (isValidTheme(cookieTheme)) {
    return cookieTheme;
  }

  const localStorageTheme = window.localStorage?.getItem('theme');
  if (isValidTheme(localStorageTheme)) {
    return localStorageTheme;
  }

  return THEME_SYSTEM;
};

/**
 * Set Nautobot theme.
 * @param {('dark'|'light'|'system')} theme - Nautobot theme to be set.
 * @param {{ manual?: boolean }} [options] - Setter function options object. Currently supported option is `manual`.
 * @returns {void} Do not return any value, set given `theme` and save it into a persistent store if `manual` is `true`.
 */
const setTheme = (theme, options) => {
  const isManual = Boolean(options?.manual);

  const modal = document.getElementById(THEME_MODAL_ID);
  const buttons = modal?.querySelectorAll('button[data-nb-theme]') ?? [];

  buttons.forEach((button) =>
    ['border', 'border-primary'].forEach((className) =>
      button.classList.toggle(className, button.dataset.nbTheme === theme),
    ),
  );

  const bsTheme = theme === THEME_SYSTEM ? getPreferredColorScheme() : theme;
  document.documentElement.dataset.theme = bsTheme;
  document.documentElement.dataset.bsTheme = bsTheme;

  if (theme === THEME_SYSTEM) {
    removeCookie('theme');
    window.localStorage?.removeItem('theme');
  } else if (isManual) {
    setCookie('theme', theme);
    window.localStorage?.setItem('theme', theme);
  }

  if (theme === THEME_DARK || (theme === THEME_SYSTEM && bsTheme === THEME_DARK)) {
    [...document.getElementsByTagName('object')].forEach((object) => {
      object.addEventListener('load', (event) => {
        if (event.target.contentDocument) {
          const images = event.target.contentDocument.getElementsByTagName('image');
          const short_names = event.target.contentDocument.getElementsByClassName('rack-device-shortname');
          const full_names = event.target.contentDocument.getElementsByClassName('rack-device-fullname');

          [...images, ...short_names, ...full_names].forEach((rack_image) =>
            rack_image.setAttribute('filter', 'url(#darkmodeinvert)'),
          );
        }
      });
    });
  }

  if (isManual) {
    document.location.reload();
  }
};

export const initializeTheme = () => {
  const modal = document.getElementById(THEME_MODAL_ID);
  const buttons = modal?.querySelectorAll('button[data-nb-theme]') ?? [];

  setTheme(detectTheme());
  window.matchMedia(`(prefers-color-scheme: ${THEME_DARK})`).addEventListener('change', () => setTheme(detectTheme()));

  const onClick = (event) => setTheme(event.currentTarget.dataset.nbTheme, { manual: true });
  buttons.forEach((button) => button.addEventListener('click', onClick));

  return () => buttons.forEach((button) => button.removeEventListener('click', onClick));
};
