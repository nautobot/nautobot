import { Modal } from 'bootstrap';
import { getCookie, removeCookie, setCookie } from './cookie.js';

const THEME_MODAL_ID = 'theme_modal';

const THEME_DARK = 'dark';
const THEME_LIGHT = 'light';
const THEME_SYSTEM = 'system';

/**
 * Check if given `theme` is a valid Nautobot theme, i.e. `'dark'`, `'light'`, or `'system'`.
 * @param {string} theme - Theme in question.
 * @returns {boolean} `true` is given `theme` is a valid Nautobot theme, `false` otherwise.
 */
const isValidTheme = (theme) => theme === THEME_DARK || theme === THEME_LIGHT || theme === THEME_SYSTEM;

/**
 * Get preferred system color scheme from browser/OS settings.
 * @returns {('dark'|'light')} Preferred system color scheme.
 */
const getPreferredColorScheme = () =>
  window.matchMedia?.(`(prefers-color-scheme: ${THEME_DARK})`).matches ? THEME_DARK : THEME_LIGHT;

/**
 * Get the user's theme choice from cookies, defaulting to 'system' if not set or invalid.
 * @returns {('dark'|'light'|'system')} The user's theme choice.
 */
const getThemeChoice = () => {
  let current_theme_choice = getCookie('theme');
  if (!isValidTheme(current_theme_choice)) {
    current_theme_choice = THEME_SYSTEM;
  }
  return current_theme_choice;
};
/**
 * Determine the effective theme to be used.
 * @returns {('dark'|'light')} The effective theme.
 */
const determineTheme = () => {
  const current_theme_choice = getThemeChoice();
  let determined_theme = getPreferredColorScheme();

  // If cookie theme is valid and not 'system', we use the cookie theme.
  if (current_theme_choice !== 'system') {
    determined_theme = current_theme_choice;
  }

  // Persist the determined theme in localStorage for quick access.
  window.localStorage.setItem('theme', determined_theme);
  return determined_theme;
};

/**
 * Persist the user's theme choice in cookies.
 * @param {('dark'|'light'|'system')} theme - The user's theme choice.
 * @returns {('dark'|'light'|'system')} The persisted theme choice.
 */
const persistThemeChoice = (theme) => {
  if (isValidTheme(theme)) {
    if (theme === THEME_SYSTEM) {
      removeCookie('theme');
    } else {
      setCookie('theme', theme);
    }
  }
  return theme;
};

/**
 * Set Nautobot theme.
 * @param {('dark'|'light'|'system')} theme - Nautobot theme to be set.
 * @returns {void} Do not return any value, set given `theme` and save it into a persistent store if `manual` is `true`.
 */
const setTheme = (theme = null) => {
  let current_theme_choice = getThemeChoice();
  if (theme !== null && theme !== current_theme_choice) {
    persistThemeChoice(theme);
    current_theme_choice = theme;
  }
  const determined_theme = determineTheme();

  const modal = document.getElementById(THEME_MODAL_ID);
  const buttons = modal?.querySelectorAll('button[data-nb-theme]') ?? [];

  buttons.forEach((button) =>
    ['border', 'border-primary'].forEach((className) =>
      button.classList.toggle(className, button.dataset.nbTheme === current_theme_choice),
    ),
  );

  const bsTheme = determined_theme;
  document.documentElement.dataset.theme = bsTheme;
  document.documentElement.dataset.bsTheme = bsTheme;

  if (determined_theme === THEME_DARK) {
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
};

export const initializeTheme = () => {
  const modal = document.getElementById(THEME_MODAL_ID);
  const buttons = modal?.querySelectorAll('button[data-nb-theme]') ?? [];

  setTheme();
  window.matchMedia(`(prefers-color-scheme: ${THEME_DARK})`).addEventListener('change', () => setTheme());

  const onClick = (event) => {
    setTheme(event.currentTarget.dataset.nbTheme);
    Modal.getInstance(modal).hide();
  };
  buttons.forEach((button) => button.addEventListener('click', onClick));

  return () => buttons.forEach((button) => button.removeEventListener('click', onClick));
};
