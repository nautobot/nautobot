import { createElement, rem } from './utils.js';

const FORM_CONTROL_PADDING_X = rem(12);
const GAP = rem(6);
const ICON_SIZE = rem(20);

const BASE_SEARCH_INPUT_PADDING_X = `${FORM_CONTROL_PADDING_X + ICON_SIZE + GAP}rem`;

const MAX_BADGE_COUNT = 1;

export const initializeSearch = () => {
  const headerSearch = document.getElementById('header_search');

  // Do nothing and `return` early when there is no `#header_search` element in the page.
  if (!headerSearch) {
    return () => {};
  }

  const NAV_MENU = (() => {
    try {
      const navMenu = document.getElementById('nav_menu');
      return navMenu ? JSON.parse(navMenu.textContent) : {};
      // eslint-disable-next-line no-unused-vars
    } catch (exception) {
      return {};
    }
  })();

  /*
   * Pick only the lowest level of nested `nav_menu` object. In TypeScript, it would be manifested as the following type:
   * `{ [item_link: string]: { name: string; weight: number } };`.
   */
  const SEARCHABLE_MODELS = Object.fromEntries(
    Object.entries(NAV_MENU.tabs).flatMap(([, tab_details]) =>
      Object.entries(tab_details.groups).flatMap(([, group_details]) =>
        Object.entries(group_details.items).map(([item_link, item_details]) => [item_link, item_details]),
      ),
    ),
  );

  const BADGE_REG_EXP = new RegExp(
    `^\\s*in\\s*:\\s*(${Object.entries(SEARCHABLE_MODELS)
      // Extend simple vanilla model name match with more word delimiter variants (or no word delimiters at all).
      .flatMap(([, { name }]) => [name, ...['', '_', '\\-'].map((delimiter) => name.replace(/\s+/g, delimiter))])
      .join('|')})\\s+`,
    'i',
  );

  const headerSearchInput = headerSearch.querySelector('input');

  const closeSearchPopup = () => {
    const searchPopup = document.getElementById('search_popup');

    if (searchPopup) {
      searchPopup.remove();
      document.body.classList.toggle('overflow-y-hidden', false);
    }
  };

  // Focus search input on Cmd+K or Ctrl+K shortcut and close search popup on Escape.
  const onKeyDown = (event) => {
    const isPressedCmd = event.getModifierState?.('Meta');
    const isPressedCtrl = event.ctrlKey;

    if ((isPressedCmd || isPressedCtrl) && event.key === 'k') {
      event.preventDefault();
      headerSearchInput.focus();
    } else if (event.key === 'Escape') {
      closeSearchPopup();
    }
  };

  document.addEventListener('keydown', onKeyDown);

  const openSearchPopup = () => {
    const searchPopup = document.getElementById('search_popup');

    // Just focus an existing search popup `input` and `return` early if `#searchPopup` is already open.
    if (searchPopup) {
      const input = searchPopup.querySelector('input');
      input?.focus();
      input?.setSelectionRange(-1, -1);
      return;
    }

    document.body.classList.toggle('overflow-y-hidden', true);

    const { left: mainLeft = 0, right: mainRight = 0 } = document.querySelector('main')?.getBoundingClientRect() ?? {};
    const { top: headerSearchInputTop } = headerSearchInput.getBoundingClientRect();

    const icon = createElement('span', {
      'aria-hidden': 'true',
      className:
        'mdi mdi-magnify d-inline-flex ms-12 mt-6 pe-none position-absolute start-0 text-secondary top-0 user-select-none',
      style: `height: ${ICON_SIZE}rem; width: ${ICON_SIZE}rem;`,
    });

    const badges = createElement('span', {
      className: 'd-inline-flex gap-6 left-0 my-6 position-absolute top-0',
      style: `left: ${BASE_SEARCH_INPUT_PADDING_X};`,
    });

    const input = createElement('input', {
      className: 'form-control w-100',
      name: 'q',
      required: 'true',
      style: `padding-inline: ${BASE_SEARCH_INPUT_PADDING_X};`,
      type: 'search',
      value: headerSearchInput.value,
    });

    const clear = createElement(
      'button',
      {
        className: `btn mdi mdi-close bg-transparent border-0 end-0 hstack justify-content-center me-12 mt-6 p-0 position-absolute text-secondary top-0 nb-transition-base${input.value === '' ? ' invisible opacity-0' : ''}`,
        style: `height: ${ICON_SIZE}rem; width: ${ICON_SIZE}rem;`,
        type: 'button',
      },
      createElement('span', { className: 'visually-hidden' }, 'Clear'),
    );

    clear.addEventListener('click', () => {
      input.value = '';
      input.dispatchEvent(new InputEvent('input'));
      input.focus();
    });

    input.addEventListener('input', () => {
      const shouldHideClear = input.value === '';
      clear.classList.toggle('invisible', shouldHideClear);
      clear.classList.toggle('opacity-0', shouldHideClear);
    });

    const submit = createElement('input', { className: 'd-none', type: 'submit' });

    const form = createElement(
      'form',
      { action: headerSearch.getAttribute('action'), className: 'position-relative w-100', role: 'search' },
      icon,
      badges,
      input,
      clear,
      submit,
    );

    /* In case there is no badge, use global search. Otherwise, navigate to badge specific model list view. */
    form.addEventListener('submit', () => {
      const badge = form.querySelector('[data-nb-link]:last-child');

      if (badge) {
        form.setAttribute('action', badge.dataset.nbLink);
      }
    });

    const results = createElement('div');

    const popup = createElement(
      'div',
      { className: 'mx-auto w-100', style: `max-width: ${rem(720)}rem;` },
      form,
      results,
    );

    const overlay = createElement(
      'div',
      {
        className: 'overflow-auto pb-20 position-fixed top-0 end-0 bottom-0 start-0 nb-z-modal-backdrop',
        id: 'search_popup',
        role: 'dialog',
        style: `background-color: rgba(0, 0, 0, .5); padding-block-start: ${headerSearchInputTop}px; padding-inline-start: calc(${mainLeft}px + ${rem(20)}rem); padding-inline-end: calc(100% - ${mainRight}px + ${rem(20)}rem);`,
      },
      popup,
    );

    // Close search popup on direct overlay click.
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) {
        closeSearchPopup();
      }
    });

    document.body.appendChild(overlay);

    const addBadge = (link) => {
      const name = Object.entries(SEARCHABLE_MODELS).find(([item_link]) => item_link === link)?.[1]?.name ?? link;

      const removeButton = createElement(
        'button',
        { type: 'button' },
        createElement('span', { 'aria-hidden': 'true', class: 'mdi mdi-close' }),
        createElement('span', { class: 'visually-hidden' }, 'Remove'),
      );

      const badge = createElement(
        'span',
        { className: 'badge border', 'data-nb-link': link },
        `in: ${name}`,
        removeButton,
      );

      removeButton.addEventListener('click', () => {
        badge.remove();
        input.focus();
      });

      // Before adding a new badge, remove existing badges with the same `link` to prevent duplicates.
      [...badges.querySelectorAll(`[data-nb-link="${link}"]`)].forEach((existing) => existing.remove());

      badges.appendChild(badge);

      // Obey the `MAX_BADGE_COUNT` constraint.
      [...badges.children].slice(0, -1 * MAX_BADGE_COUNT).forEach((child) => child.remove());
    };

    // Recalculate search input left padding when badges container size changes, i.e. a badge is added or removed.
    const resizeObserver = new ResizeObserver(() => {
      const { width } = badges.getBoundingClientRect();
      input.style.paddingInlineStart = width
        ? `calc(${BASE_SEARCH_INPUT_PADDING_X} + ${width}px + ${GAP}rem)`
        : BASE_SEARCH_INPUT_PADDING_X;
    });

    resizeObserver.observe(badges);

    input.addEventListener('input', () => {
      const match = input.value.match(BADGE_REG_EXP);

      if (match) {
        const [phrase, model] = match;

        const normalize = (text) =>
          text
            .trim()
            .toLowerCase()
            .replace(/\s|_|-/g, '');
        const link = Object.entries(SEARCHABLE_MODELS).find(
          ([, { name }]) => normalize(name) === normalize(model),
        )?.[0];

        if (link) {
          // Remove phrase that matched the badge-specific regular expression and replace it with a corresponding badge.
          input.value = input.value.replace(phrase, '');
          input.dispatchEvent(new InputEvent('input'));
          addBadge(link);
        }
      }
    });

    // Remove the first badge on the right-hand side when `'Backspace'` key is pressed on the input start position.
    input.addEventListener('keydown', (event) => {
      const isBackspace = event.key === 'Backspace';
      const isInputStart = input.selectionEnd === 0 && input.selectionStart === 0;

      if (isBackspace && isInputStart) {
        badges.querySelector(':last-child')?.remove();
      }
    });

    // When search popup is open, copy existing badges from `#header_search` to search popup input.
    headerSearch.querySelectorAll('[data-nb-link]').forEach((badge) => addBadge(badge.dataset.nbLink));

    // Automatically focus search popup input when opened and move cursor to the end of input field.
    input.focus();
    input.setSelectionRange(-1, -1);
  };

  headerSearchInput.addEventListener('focus', openSearchPopup);

  return () => {
    closeSearchPopup();
    document.removeEventListener('keydown', onKeyDown);
    headerSearchInput.removeEventListener('focus', openSearchPopup);
  };
};
