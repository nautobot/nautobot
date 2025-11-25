import { Modal } from 'bootstrap';
import { getCookie, setCookie } from './cookie.js';

const THEME_MODAL_ID = 'theme_modal';

const THEME_DARK = 'dark';
const THEME_LIGHT = 'light';
const THEME_SYSTEM = 'system';

const THEME_CHOICE_COOKIE_NAME = 'theme_choice';
const THEME_DETERMINED_COOKIE_NAME = 'theme';

/**
 * Check if given `theme_choice` is a valid theme choice, i.e. `'dark'`, `'light'`, or `'system'`:
 * - 'dark' for always dark mode
 * - 'light' for always light mode
 * - 'system' to follow the system/browser preference, getPreferredColorScheme() will determine actual theme
 * @param {string} theme_choice - Choice in question.
 * @returns {boolean} `true` is given `theme_choice` is a valid Nautobot theme, `false` otherwise.
 */
const isValidThemeChoice = (theme_choice) => [THEME_DARK, THEME_LIGHT, THEME_SYSTEM].includes(theme_choice);

/**
 * Get preferred system color scheme from browser/OS settings.
 * @returns {('dark'|'light')} Preferred system color scheme.
 */
const determineBrowserPreference = () =>
  window.matchMedia?.(`(prefers-color-scheme: ${THEME_DARK})`).matches ? THEME_DARK : THEME_LIGHT;

/**
 * Determine the effective theme to be used.
 * @returns {('dark'|'light')} The effective theme.
 */
const determineTheme = () => {
  const current_theme_choice = getCookie(THEME_CHOICE_COOKIE_NAME);
  if ([THEME_DARK, THEME_LIGHT].includes(current_theme_choice)) {
    // An explicit choice of dark or light mode.
    return current_theme_choice;
  }
  // Follow the system/browser preference by default ('system' choice or invalid choice).
  return determineBrowserPreference();
};

/**
 * Persist the user's theme choice in cookie.
 * @param {('dark'|'light'|'system')} theme - The user's theme choice.
 * @returns {void} Do not return any value
 */
const persistThemeChoice = (theme) => {
  if (isValidThemeChoice(theme)) {
    setCookie(THEME_CHOICE_COOKIE_NAME, theme, { 'max-age': 31536000, path: '/' }); // 1 year
  }
};

/**
 * Handle syntax highlighter theme change.
 * @param {('dark'|'light')} theme - The effective theme.
 * @returns {void} Do not return any value
 */
const handleSyntaxHighlighterThemeChange = (theme) => {
  // Since the syntax highlighter stylesheet is loaded via a <link> tag, we need to swap out the href to change themes.
  // The best fix would be to have both stylesheets loaded and use media queries to switch between them, similar to how we do for the main Nautobot theme.
  const highlighterLinks = document.querySelectorAll('link[rel="stylesheet"][href*="github"]');
  if (highlighterLinks.length === 1) {
    // We send two stylesheets on the initial page with media queries, but after that only one is present which we need to swap out.
    const [syntaxLinkElement] = highlighterLinks;
    const css_file = theme === THEME_DARK ? 'github-dark.min.css' : 'github.min.css';
    syntaxLinkElement.href = syntaxLinkElement.href.replace(/github(-dark)?\.min\.css/, css_file);
  }
};

/**
 * Handle Echarts theme change.
 * @param {('dark'|'light')} theme - The effective theme.
 * @returns {void} Do not return any value
 */
const handleEchartsThemeChange = (theme) => {
  // If using Echarts, we need to update the theme there as well.
  const echart_instances = document.querySelectorAll('div[_echarts_instance_]');
  echart_instances?.forEach((instance) => {
    const options = JSON.parse(document.getElementById(`echarts-config-${instance.id}`).textContent);
    const colors = Array.isArray(options.color)
      ? options.color.map((colorObj) => colorObj?.[theme] || colorObj?.light || colorObj)
      : options.color;
    window.echarts.getInstanceByDom(instance)?.setOption({
      color: colors,
      darkMode: theme === THEME_DARK,
    });
  });
};

/**
 * Set Nautobot theme.
 * @param {('dark'|'light'|'system'|null)} theme - Nautobot theme to be set. If `null`, determine theme based on existing user choice or system preference.
 * @returns {void} Do not return any value, set given `theme` and save it into a persistent store if `manual` is `true`.
 */
const setTheme = (theme = null) => {
  if (theme !== null && isValidThemeChoice(theme)) {
    // An explicit theme was provided, so we persist the choice.
    persistThemeChoice(theme);
  }
  const current_theme_choice = getCookie(THEME_CHOICE_COOKIE_NAME); // The user's choice for the purpose of button highlighting.
  const determined_theme = determineTheme(); // The effective theme to be applied.

  // Persist the determined theme for server-side rendering purposes.
  setCookie(THEME_DETERMINED_COOKIE_NAME, determined_theme, { 'max-age': 31536000, path: '/' }); // 1 year

  const modal = document.getElementById(THEME_MODAL_ID);
  const buttons = modal?.querySelectorAll('button[data-nb-theme]') ?? [];

  buttons.forEach((button) =>
    ['border', 'border-primary'].forEach((className) =>
      button.classList.toggle(className, button.dataset.nbTheme === current_theme_choice),
    ),
  );

  document.documentElement.dataset.theme = determined_theme;
  document.documentElement.dataset.bsTheme = determined_theme;

  handleSyntaxHighlighterThemeChange(determined_theme);
  handleEchartsThemeChange(determined_theme);

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

const handleThemeChoiceUpgradeAndSetDefault = () => {
  /**
   * We need to handle the "upgrade" scenario:
   * - Prior to Nautobot 3.0, the `theme` cookie was a Session cookie so not persisted.
   * - localStorage was where a user's choice was "stored"
   *
   * In Nautobot 3.0+, we will do away with localStorage and instead move the user's choice to a persistent cookie, `theme_choice`.
   * We will also keep the `theme` cookie as the "determined" theme for server-side rendering purposes.
   * Generally we shouldn't need this as good media queries should handle it, but it's here for completeness.
   * For example, some SVG renderings on the server may need to know the theme.
   *
   * To handle this upgrade scenario, we will:
   * 1. Check if `theme_choice` cookie exists. If it does, we assume the user has already "upgraded" and do nothing.
   * 2. If `theme_choice` cookie does not exist, we check localStorage for the user's theme choice.
   * 3. If localStorage has a valid theme choice, we persist it to the `theme_choice` cookie.
   * 4. Finally, we remove the theme from localStorage to complete the migration.'
   *
   * We can remove/refactor this in 4.0 for certain, but likely in 3.1+.
   *
   * In that scenario, if the theme_choice cookie is missing, we can default to 'system' without checking localStorage.
   */

  const themeChoiceCookie = getCookie(THEME_CHOICE_COOKIE_NAME);
  if (!isValidThemeChoice(themeChoiceCookie)) {
    // If theme_choice cookie does not exist or is invalid, check localStorage
    const localStorageTheme = window.localStorage?.getItem('theme');

    // If localStorage theme is valid, we use it, else we default to 'system';
    // Note: we always removed the localStorage to imply the 'system' choice so technically we should only check for 'dark' or 'light' here, but we validate just in case.
    const theme_choice_to_set = isValidThemeChoice(localStorageTheme) ? localStorageTheme : THEME_SYSTEM;

    setCookie(THEME_CHOICE_COOKIE_NAME, theme_choice_to_set, { 'max-age': 31536000, path: '/' }); // 1 year
  }
  // Else: If theme_choice cookie exists and is valid, we don't need to do any migration.
  // Regardless, we remove localStorage to complete migration, on the off chance it still exists.
  window.localStorage?.removeItem('theme');
};

export const initializeTheme = () => {
  const modal = document.getElementById(THEME_MODAL_ID);
  const buttons = modal?.querySelectorAll('button[data-nb-theme]') ?? [];

  handleThemeChoiceUpgradeAndSetDefault();
  setTheme();

  window.matchMedia(`(prefers-color-scheme: ${THEME_DARK})`).addEventListener('change', () => setTheme());

  const onClick = (event) => {
    setTheme(event.currentTarget.dataset.nbTheme);
    Modal.getInstance(modal).hide();
  };
  buttons.forEach((button) => button.addEventListener('click', onClick));

  return () => buttons.forEach((button) => button.removeEventListener('click', onClick));
};
