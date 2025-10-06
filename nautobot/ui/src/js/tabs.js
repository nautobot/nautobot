import * as bootstrap from 'bootstrap';
import { createElement, removeElementClasses } from './utils.js';

const TABS_HIDDEN_CLASSES = ['invisible', 'position-absolute'];

/**
 * Collapse wrapped tabs to dropdown menu in given tab container.
 * @param {HTMLElement} tabs - Tab container HTML element.
 * @returns {void} Do not return any value, modify DOM instead.
 */
export const collapseTabs = (tabs) => {
  const tabsParent = tabs.parentNode;

  // Remove existing tab clones to prevent duplicates because they will be created from scratch below if needed.
  [...tabsParent.querySelectorAll('.nav.nav-tabs[data-clone="true"]')].forEach((tabsClone) => tabsClone.remove());

  // For safety, do not operate on original tabs element, deep clone tabs to operate on its clone instead.
  const tabsClone = tabs.cloneNode(true);

  // Remove `id` element attribute from cloned tabs element to avoid potential `id` conflicts.
  tabsClone.removeAttribute('id');

  // Set `data-clone` attribute to `"true"` on tabs clone element to be able to easily distinguish it from the original.
  tabsClone.dataset.clone = 'true';

  /*
   * Add following classes to cloned element to:
   *   1. Make tabs span across the whole required width without wrapping.
   *   2. Force them to be (temporarily) invisible.
   */
  const tabsCloneTemporaryClasses = ['flex-nowrap', 'invisible', 'position-absolute', 'z-n1'];
  tabsClone.classList.add(...tabsCloneTemporaryClasses);

  // Append currently invisible cloned tabs to DOM right after the original tabs element.
  if (tabs.nextSibling) {
    tabsParent.insertBefore(tabsClone, tabs.nextSibling);
  } else {
    tabsParent.appendChild(tabsClone);
  }
  // Excessive tabs should be collapsed if tabs clone is wider than the original. Remember - clone does not wrap.
  const shouldCollapseTabs = () => tabsClone.getBoundingClientRect().width > tabs.getBoundingClientRect().width;

  // If there is no need to collapse tabs, show original tabs (if previously hidden) clean up tabs clone and `return` early.
  if (!shouldCollapseTabs()) {
    tabs.classList.remove(...TABS_HIDDEN_CLASSES);
    tabsParent.removeChild(tabsClone);
    return;
  }

  /*
   * Compose dropdown element. Ignore dropdown items for now, they will be added to the dropdown menu soon anyway. The
   * most important thing about this step is to append dropdown with visible toggle button at the end of cloned tabs
   * list to reach maximum width (dropdown toggle has considerable size too) before starting to actually collapse tabs.
   */
  const dropdownMenu = createElement('ul', { className: 'dropdown-menu dropdown-menu-end' });
  const dropdownToggleIcon = createElement('span', { className: 'mdi mdi-menu' });
  const dropdownToggleLabel = createElement('span', { className: 'visually-hidden' }, 'Toggle Dropdown');
  const dropdownToggle = createElement(
    'button',
    {
      'aria-expanded': 'false',
      className: 'btn dropdown-toggle text-secondary',
      'data-bs-toggle': 'dropdown',
      type: 'button',
    },
    dropdownToggleIcon,
    dropdownToggleLabel,
  );
  const dropdown = createElement(
    'li',
    { className: 'dropdown flex-grow-1 mb-n1 text-end' },
    dropdownToggle,
    dropdownMenu,
  );
  tabsClone.appendChild(dropdown);

  /*
   * Identify tabs that require collapsing by taking out one by one from the right-hand side until tabs width can fit
   * inside its parent container. Essentially, overflowing tabs are moved from tab list to future dropdown menu.
   */
  const collapsedTabs = [];
  while (shouldCollapseTabs()) {
    const lastTab = dropdown.previousElementSibling; // With dropdown appended to DOM, its previous siblings are tabs.
    collapsedTabs.unshift(lastTab); // Use `unshift` instead of `push` because this loop is iterating backward in a sense.
    tabsClone.removeChild(lastTab);
  }

  /*
   * Properly convert collapsed tabs to dropdown items:
   *   1. Remove all `<li>` `nav-item` element classes.
   *   2. Remove all `<a>` `nav-link` element classes other than `active` and `disabled` to maintain valid tab state.
   *   3. Add `dropdown-item` class to `<a>` element (formerly `nav-link`).
   *   4. Append collapsed tab to dropdown menu.
   */
  collapsedTabs.forEach((collapsedTab) => {
    removeElementClasses(collapsedTab);

    [...collapsedTab.children].forEach((navLink) => {
      removeElementClasses(navLink, 'active', 'disabled');
      navLink.classList.add('dropdown-item', 'justify-content-between');
    });

    dropdownMenu.appendChild(collapsedTab);
  });

  /*
   * Tabs clone with collapsed tabs is now ready to be swapped with original. The only thing left to do is to
   * make it synchronize its state back to the original.
   */
  [...tabsClone.querySelectorAll('a')].forEach((clonedTab) => {
    clonedTab.addEventListener('shown.bs.tab', () => {
      const originalTab = tabs.querySelector(`a[href="${clonedTab.getAttribute('href')}"]`);
      const originalTabInstance = bootstrap.Tab.getInstance(originalTab) || new bootstrap.Tab(originalTab);
      originalTabInstance.show();
    });
  });

  // Swap tabs clone with the original, in other words swap wrapped tabs with collapsed tabs.
  tabs.classList.add(...TABS_HIDDEN_CLASSES);
  tabsClone.classList.remove(...tabsCloneTemporaryClasses);
};

/**
 * Observe size changes of all tab containers on the page and collapse tabs inside of them if they wrap.
 * @example
 * // Run `collapseTabs` algorithm for all tabs on the page exactly once, i.e. observe and immediately unobserve.
 * const unobserveCollapseTabs = observeCollapseTabs();
 * unobserveCollapseTabs();
 * @returns {function(): void} Unobserve function - disconnect all resize observers created during function call.
 */
export const observeCollapseTabs = () => {
  const resizeObservers = [...document.querySelectorAll('.nav.nav-tabs')].map((tabs) => {
    const resizeObserver = new ResizeObserver(() => collapseTabs(tabs));
    resizeObserver.observe(tabs);
    return resizeObserver;
  });

  return () => resizeObservers.forEach((resizeObserver) => resizeObserver.disconnect());
};
