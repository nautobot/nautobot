import { createElement } from './utils.js';

export const initializeSearch = () => {
  const headerSearch = document.getElementById('header_search');
  const input = headerSearch.querySelector('input');
  const placeholder = headerSearch.querySelector('input + span > span');

  const togglePlaceholder = () => placeholder.classList.toggle('d-none', input.value !== '');
  input.addEventListener('input', togglePlaceholder);
  togglePlaceholder();

  document.addEventListener('keydown', (event) => {
    const isPressedCmd = event.getModifierState('Meta');
    const isPressedCtrl = event.ctrlKey;

    if ((isPressedCmd || isPressedCtrl) && event.key === 'k') {
      event.preventDefault();
      input.focus();
    }
  });

  const openSearchPopup = () => {
    document.body.classList.toggle('overflow-y-hidden', true);

    const { left: mainLeft, right: mainRight } = document.querySelector('main').getBoundingClientRect();
    const { left: inputLeft, top: inputTop } = input.getBoundingClientRect();

    const searchPopupInput = createElement('input', {
      className: 'form-control w-100',
      style: `padding-inline-start: ${input.style.paddingInlineStart};`,
      value: input.value,
    });

    const searchPopupInputIcon = createElement('span', {
      className: 'mdi mdi-magnify d-inline-flex h-20 ms-12 mt-6 position-absolute start-0 text-secondary top-0 w-20',
    });

    const searchPopupInputWrapper = createElement(
      'div',
      { className: 'position-relative w-100' },
      searchPopupInput,
      searchPopupInputIcon,
    );

    const searchPopupResults = createElement('div');

    const searchPopup = createElement(
      'div',
      { className: 'mx-auto w-100', style: 'max-width: 45rem;' },
      searchPopupInputWrapper,
      searchPopupResults,
    );

    const searchPopupOverlay = createElement(
      'div',
      {
        className: 'overflow-auto pb-20 position-fixed top-0 end-0 bottom-0 start-0 nb-z-modal-backdrop',
        role: 'dialog',
        style: `background-color: rgba(0, 0, 0, .5); padding-block-start: ${inputTop}px; padding-inline-start: calc(${mainLeft}px + 1.25rem); padding-inline-end: calc(100% - ${mainRight}px + 1.25rem);`,
      },
      searchPopup,
    );

    document.body.appendChild(searchPopupOverlay);

    const closeSearchPopup = () => {
      searchPopupOverlay.remove();
      document.body.classList.toggle('overflow-y-hidden', false);
    };

    // Close search popup on Escape key press.
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeSearchPopup();
      }
    });

    // Close search popup on direct overlay click.
    searchPopupOverlay.addEventListener('click', (event) => {
      if (event.currentTarget === event.target) {
        closeSearchPopup();
      }
    });

    // Automatically focus search popup input when opened.
    searchPopupInput.focus();

    searchPopupInput.addEventListener('input', (event) => {
      const match = new RegExp(`in:\w*`).test(event.currentTarget.value);
      if (match) {
      }
    });
  };

  input.addEventListener('focus', openSearchPopup);
};
