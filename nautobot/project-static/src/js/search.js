import { bettertitle, createElement, rem } from './utils.js';

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

  const SEARCH_MODEL_CHOICES = (() => {
    try {
      const searchModelChoices = document.getElementById('search_model_choices');
      return searchModelChoices ? JSON.parse(searchModelChoices.textContent) : [];
    } catch (exception) {
      return [];
    }
  })();

  const SEARCHABLE_MODELS = SEARCH_MODEL_CHOICES.flatMap(([app_config, model_tuples]) =>
    Array.isArray(model_tuples) ? model_tuples : [],
  );

  const BADGE_REG_EXP = new RegExp(
    `^\\s*in\\s*:\\s*(${SEARCHABLE_MODELS.flatMap((searchableModel) => searchableModel).join('|')})\\s+`,
    'i',
  );

  const headerSearchInput = headerSearch.querySelector('input');
  const headerSearchPlaceholder = headerSearch.querySelector('input + span > span:last-child');

  // Toggle between placeholder and value in global header search input.
  const shouldShowValue = headerSearchInput.value !== '';
  headerSearchInput.classList.toggle('nb-color-transparent', !shouldShowValue);
  headerSearchInput.style.paddingInlineStart = `${headerSearchPlaceholder.offsetLeft}px`;
  headerSearchPlaceholder.classList.toggle('invisible', shouldShowValue);

  const closeSearchPopup = () => {
    const searchPopup = document.getElementById('search_popup');

    if (searchPopup) {
      searchPopup.remove();
      document.body.classList.toggle('overflow-y-hidden', false);
    }
  };

  // Focus search input on Cmd+K or Ctrl+K shortcut and close search popup on Escape.
  const onKeyDown = (event) => {
    const isPressedCmd = event.getModifierState('Meta');
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
    document.body.classList.toggle('overflow-y-hidden', true);

    const { left: mainLeft = 0, right: mainRight = 0 } = document.querySelector('main')?.getBoundingClientRect() ?? {};
    const { top: inputTop } = headerSearchInput.getBoundingClientRect();

    const searchIcon = createElement('span', {
      className: 'mdi mdi-magnify d-inline-flex ms-12 mt-6 position-absolute start-0 text-secondary top-0',
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

    const clear = createElement('button', {
      className: `btn mdi mdi-close bg-transparent border-0 end-0 hstack justify-content-center me-12 mt-6 p-0 position-absolute text-secondary top-0 nb-transition-base${input.value === '' ? ' invisible opacity-0' : ''}`,
      style: `height: ${ICON_SIZE}rem; width: ${ICON_SIZE}rem;`,
      type: 'button',
    });

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
      searchIcon,
      badges,
      input,
      clear,
      submit,
    );

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
        style: `background-color: rgba(0, 0, 0, .5); padding-block-start: ${inputTop}px; padding-inline-start: calc(${mainLeft}px + ${rem(20)}rem); padding-inline-end: calc(100% - ${mainRight}px + ${rem(20)}rem);`,
      },
      popup,
    );

    document.body.appendChild(overlay);

    // Close search popup on direct overlay click.
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) {
        closeSearchPopup();
      }
    });

    const addBadge = (modelname) => {
      const verbose_name_plural =
        SEARCHABLE_MODELS.find((searchableModel) => searchableModel[0] === modelname)?.[1] ?? modelname;

      const inputHidden = createElement('input', { name: 'obj_type', type: 'hidden', value: modelname });

      const removeButton = createElement(
        'button',
        { type: 'button' },
        createElement('span', { class: 'mdi mdi-close' }),
      );

      removeButton.addEventListener('click', () => {
        badge.remove();
        input.focus();
      });

      const badge = createElement(
        'span',
        { className: 'badge border', ['data-nb-modelname']: modelname },
        `in: ${bettertitle(verbose_name_plural)}`,
        inputHidden,
        removeButton,
      );

      // Before adding a new badge, remove existing badges with the same `modelname` to prevent duplicates.
      [...badges.querySelectorAll(`[data-nb-modelname="${modelname}"]`)].forEach((badge) => badge.remove());

      badges.appendChild(badge);

      // Obey the `MAX_BADGE_COUNT` constraint.
      [...badges.children].slice(0, -1 * MAX_BADGE_COUNT).forEach((badge) => badge.remove());
    };

    // Recalculate search input left padding when badges container size changes, i.e. a badge is added or removed.
    const resizeObserver = new ResizeObserver(() => {
      const { width } = badges.getBoundingClientRect();
      input.style.paddingInlineStart = width
        ? `calc(${BASE_SEARCH_INPUT_PADDING_X} + ${width}px + ${GAP}rem)`
        : BASE_SEARCH_INPUT_PADDING_X;
    });

    resizeObserver.observe(badges);

    input.addEventListener('input', (event) => {
      const match = input.value.match(BADGE_REG_EXP);

      if (match) {
        const [phrase, model] = match;

        // Match entered `model` to either an existing `modelname` or `verbose_name_plural` from `search_model_choices`.
        const normalize = (text) => text.trim().toLowerCase();
        const modelname = SEARCHABLE_MODELS.find((names) => names.map(normalize).includes(normalize(model)))?.[0];

        if (modelname) {
          // Remove phrase that matched the badge-specific regular expression and replace it with a corresponding badge.
          input.value = input.value.replace(phrase, '');
          input.dispatchEvent(new InputEvent('input'));
          addBadge(modelname);
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

    // When search popup is open, move existing badges from `#header_search` to search popup input.
    headerSearch.querySelectorAll('[data-nb-modelname]').forEach((badge) => addBadge(badge.dataset.nbModelname));

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
