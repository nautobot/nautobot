import Fuse from 'fuse.js';
import { createElement, rem } from './utils.js';

const FORM_CONTROL_PADDING_X = rem(12);
const GAP = rem(6);
const ICON_SIZE = rem(20);

const BASE_SEARCH_INPUT_PADDING_X = `${FORM_CONTROL_PADDING_X + ICON_SIZE + GAP}rem`;

const MAX_BADGE_COUNT = 1;
const MAX_TYPEAHEAD_RESULT_COUNT = 3;

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

  const IN_REG_EXP = /^\s*in\s*(:|\s|$)\s*/;
  const BADGE_REG_EXP = new RegExp(
    `${IN_REG_EXP.source}(${Object.entries(SEARCHABLE_MODELS)
      // Extend simple vanilla model name match with more word delimiter variants (or no word delimiters at all).
      .flatMap(([, { name }]) => [name, ...['', '_', '\\-'].map((delimiter) => name.replace(/\s+/g, delimiter))])
      .join('|')})\\s+`,
    'i',
  );

  const fuse = new Fuse(
    Object.entries(SEARCHABLE_MODELS).map(([item_link, item_details]) => ({ item_link, name: item_details?.name })),
    { keys: ['name'], threshold: 0.4, useTokenSearch: true },
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
      autocomplete: 'off',
      className: 'form-control w-100',
      name: 'q',
      required: 'true',
      role: 'searchbox',
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
      { action: headerSearch.getAttribute('action'), className: 'pe-auto position-relative w-100', role: 'search' },
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

    /*
     * `inputHeight` calculation below may seem obscure and in fact it would be simpler to do in SCSS, but since search
     * is mostly a JavaScript feature, let's not scatter its parts over multiple places. Anyway, the formula is:
     * `fontSize=0.875rem=14px * lineHeight=1.4375 + (paddingY=0.3125rem=5px + borderY=var(--bs-border-width)=0.0625rem=1px) * 2`
     */
    const inputHeight = `calc(0.875rem * 1.4375 + (0.3125rem + var(--bs-border-width)) * 2)`;
    const results = createElement('div', {
      className: 'bg-body mt-10 overflow-x-hidden overflow-y-auto pe-auto rounded w-100',
      style: `max-height: calc(100% - 0.625rem - ${inputHeight});`, // `0.625rem` subtraction compensates for `mt-10`.
    });

    const popup = createElement(
      'div',
      { className: 'h-100 mx-auto pe-none w-100', style: `max-width: ${rem(720)}rem;` },
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

    const getResultItems = () => [...results.querySelectorAll('.nb-search-list-group-item')];

    const isResultItemActive = (item) => item.classList.contains('active');

    const isResultItemTentativelySelected = (item) => item.getAttribute('aria-selected') === 'true';

    /*
     * There is a distinction between `class="... active"` and `aria-selected="true"` that needs to be called out here.
     * When an item is `active`, it only serves visual highlight purpose (and optionally to start the *tentative*
     * keyboard navigation from there when down/up arrow key is pressed). When an item has `aria-selected="true"`
     * attribute, it actually is *tentatively* selected. In such case, for example, when Enter key is pressed, the
     * tentatively selected item action is prioritized over the standard search form submission.
     */
    const toggleResultItemActive = (item, active, tentativelySelect) => {
      const isActive = item?.classList.toggle('active', active);
      item?.setAttribute('aria-selected', String(Boolean(tentativelySelect && isActive)));
    };

    const toggleResultsVisible = (force) => {
      // Because classes used here are actually hiding the results list, need to logically flip the `force` argument.
      const args = typeof force === 'boolean' ? [!force] : [];
      const isHidden = results.classList.toggle('invisible', ...args);

      if (isHidden) {
        // When results are hidden, cancel any existing result item selection.
        getResultItems().forEach((item) => toggleResultItemActive(item, false));
      }
    };

    // Recalculate search input left padding when badges container size changes, i.e. a badge is added or removed.
    const resizeObserver = new ResizeObserver(() => {
      const { width } = badges.getBoundingClientRect();
      input.style.paddingInlineStart = width
        ? `calc(${BASE_SEARCH_INPUT_PADDING_X} + ${width}px + ${GAP}rem)`
        : BASE_SEARCH_INPUT_PADDING_X;
    });

    resizeObserver.observe(badges);

    input.addEventListener('click', () => {
      toggleResultsVisible(true); // Show results list when search input is clicked (not focused!).
    });

    input.addEventListener('input', () => {
      toggleResultsVisible(true); // Always force show results list when users are typing.

      const isPhraseIn = input.value.match(IN_REG_EXP);
      if (isPhraseIn) {
        /*
         * Phrases that start with `'in'` are treated as a special case of looking for the best searchable model match,
         * rather than executing a standard search query. Two scenarios are being covered here:
         *   1. Exact match: matches a specific model by its exact name immediately if such is found.
         *   2. Fuzzy search: looks for the closest match in searchable models and displays result list to choose from.
         */

        const exact = input.value.match(BADGE_REG_EXP);
        if (exact) {
          const [phrase, , model] = exact; // Omit the middle item as it is an irrelevant `RegExp` group.

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

          return;
        }

        const fuzzy = fuse.search(input.value.replace(IN_REG_EXP, ''), { limit: MAX_TYPEAHEAD_RESULT_COUNT });
        if ((fuzzy?.length ?? 0) > 0) {
          const typeaheadResultItems = fuzzy.map(({ item }) => {
            const itemIcon = createElement('span', {
              'aria-hidden': 'true',
              className: 'mdi mdi-magnify text-secondary',
            });
            const itemBadge = createElement('span', { className: 'badge border' }, `in: ${item.name}`);
            const itemButton = createElement(
              'button',
              { 'aria-selected': 'false', className: 'nb-search-list-group-item', type: 'button' },
              itemIcon,
              itemBadge,
            );
            itemButton.addEventListener('click', () => {
              addBadge(item.item_link);
              input.value = '';
              input.dispatchEvent(new InputEvent('input'));
              input.focus();
            });
            return createElement('li', {}, itemButton);
          });
          const typeaheadResults = createElement('ul', { className: 'nb-search-list-group' }, ...typeaheadResultItems);
          [...results.querySelectorAll('.nb-search-list-group')].map((element) => element.remove());
          results.appendChild(typeaheadResults);
          return;
        }

        results.replaceChildren(); // Remove all search results.
        return;
      }

      results.replaceChildren(); // Remove all search results.
    });

    // Most (if not all!) of the keyboard navigation is heavily inspired by Google Search.
    // eslint-disable-next-line complexity
    input.addEventListener('keydown', (event) => {
      const isArrowDown = event.key === 'ArrowDown';
      const isArrowLeft = event.key === 'ArrowLeft';
      const isArrowRight = event.key === 'ArrowRight';
      const isArrowUp = event.key === 'ArrowUp';
      const isBackspace = event.key === 'Backspace';
      const isEnter = event.key === 'Enter';
      const isEscape = event.key === 'Escape';
      const isInputStart = input.selectionEnd === 0 && input.selectionStart === 0;
      const isShowingResults = results.children.length > 0 && !results.classList.contains('invisible');

      // It is easier here to reason about individual switch cases than if/else statements and/or early returns.
      switch (true) {
        // *Tentatively* browse through the results with down/up arrow keys.
        case (isArrowDown || isArrowUp) && isShowingResults: {
          event.preventDefault(); // Prevent default to stop search input cursor from moving around.
          const items = getResultItems();
          const index = items.findIndex(isResultItemActive);
          const direction = isArrowDown ? 1 : -1;
          /*
           * There is no result item selected when `index` is less than `0` (`-1`). In that case, need to start from the
           * first item when the key pressed was `ArrowDown`, or the last item when it was `ArrowUp`. Otherwise, use the
           * standard `index + direction`.
           */
          const next = index < 0 ? index + Number(isArrowDown) : index + direction;
          /*
           * Make sure that when `next` is greater than or equal to `items.length`, it is properly reset and always
           * stays within the array index range. For valid index values, it is effectively a no-op.
           */
          const target = next % items.length;
          /*
           * Move *tentative* selection from item at initial `index` (if any) to item at calculated `target` index.
           * Using `items.at(...)` instead of direct access `items[...]` for negative array index support.
           */
          toggleResultItemActive(items.at(index), false);
          toggleResultItemActive(items.at(target), true, true);
          items.at(target)?.scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'start' });
          break;
        }

        // When results are hidden and down/up arrow key is pressed, do not browse the results yet, just show them.
        case (isArrowDown || isArrowUp) && !isShowingResults: {
          event.preventDefault(); // Prevent default to stop search input cursor from moving around.
          toggleResultsVisible(true);
          break;
        }

        // Cancel any *tentative* selection when left/right arrow key is pressed.
        case (isArrowLeft || isArrowRight) && isShowingResults: {
          const items = getResultItems();
          const tentativelySelected = items.find(isResultItemTentativelySelected);
          toggleResultItemActive(tentativelySelected, false);
          break;
        }

        // Choose the *tentatively* selected result (if there is one) on Enter.
        case isEnter && isShowingResults: {
          const items = getResultItems();
          const tentativelySelected = items.find(isResultItemTentativelySelected);
          if (tentativelySelected) {
            event.preventDefault();
            tentativelySelected.click();
          }
          break;
        }

        // Hide the results list.
        case isEscape && isShowingResults: {
          event.preventDefault(); // Prevent default to avoid search input value from being automatically cleared.
          event.stopPropagation(); // Stop propagation to prevent the entire search popup from being closed.
          toggleResultsVisible(false);
          break;
        }

        // Remove the first badge on the right-hand side when `'Backspace'` key is pressed on the input start position.
        case isBackspace && isInputStart: {
          badges.querySelector(':last-child')?.remove();
          break;
        }

        default:
          break;
      }
    });

    // When mouse is moved over or leaves the `results` element, track the item highlight accordingly.
    const onMouseEvent = (event) => {
      const items = getResultItems();
      const active = items.find(isResultItemActive);
      const hoveredOver = event.target.closest('.nb-search-list-group-item');
      /*
       * Clear *tentative* selection from the currently `active` item, but do not move it over to the next (`hoveredOver`)
       * active item. Remember that *tentative* selection is reserved exclusively for keyboard selection.
       */
      toggleResultItemActive(active, false);
      toggleResultItemActive(hoveredOver, true);
    };
    results.addEventListener('mousemove', onMouseEvent);
    results.addEventListener('mouseleave', onMouseEvent);

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
