/**
 * Initialize collapse toggle all buttons identified by `data-nb-toggle="collapse-all"` data attribute. Collapse toggle
 * all buttons can be further configured with `data-nb-target="{collapse CSS selector}"` data attribute specifying which
 * collapse elements they control. When not explicitly set, target collapse CSS selector falls back to `".collapse"`.
 * ---
 * Critical difference between this and default Bootstrap 5 collapse implementation is that Bootstrap only supports
 * toggling individual panel states without an option to toggle them collectively. See an explanation below:
 * Bootstrap 5 on "Collapse All Groups" button click:  |  Nautobot on "Collapse All Groups" button click:
 *   * X [expanded]  -> [collapsed]             |    * X [expanded]  -> [collapsed]
 *   * Y [collapsed] -> [expanded]              |    * Y [collapsed] -> [collapsed]
 *   * Z [expanded]  -> [collapsed]             |    * Z [expanded]  -> [collapsed]
 * ---
 * @returns {function(): void} Destructor function - remove all event listeners added during initialization.
 */
export const initializeCollapseToggleAll = () => {
  const areAll = (collapseElements, collapsedOrExpanded) =>
    collapseElements.every((element) => {
      const isCollapsed = !element.classList.contains('show');
      return collapsedOrExpanded === 'collapsed' ? isCollapsed : !isCollapsed;
    });

  const getCollapseToggleAllTargets = (collapseToggleAll) => [
    ...document.querySelectorAll(collapseToggleAll.dataset.nbTarget || '.collapse'),
  ];

  const onClick = (event) => {
    const collapseToggleAll = event.target.closest('[data-nb-toggle="collapse-all"]');

    if (collapseToggleAll) {
      getCollapseToggleAllTargets(collapseToggleAll).forEach((collapse) => {
        const collapseInstance = window.bootstrap.Collapse.getOrCreateInstance(collapse);
        const shouldCollapse = collapseToggleAll.getAttribute('aria-expanded') === 'true';

        if (shouldCollapse) {
          collapseInstance.hide();
        } else {
          collapseInstance.show();
        }
      });
    }
  };

  const onHiddenBsCollapse = () =>
    [...document.querySelectorAll('[data-nb-toggle="collapse-all"]')]
      .filter((collapseToggleAll) => areAll(getCollapseToggleAllTargets(collapseToggleAll), 'collapsed'))
      .forEach((collapseToggleAll) => {
        collapseToggleAll.setAttribute('aria-expanded', 'false');
        collapseToggleAll.textContent = 'Expand All Groups';
      });

  const onShownBsCollapse = () =>
    [...document.querySelectorAll('[data-nb-toggle="collapse-all"]')]
      .filter((collapseToggleAll) => areAll(getCollapseToggleAllTargets(collapseToggleAll), 'expanded'))
      .forEach((collapseToggleAll) => {
        collapseToggleAll.setAttribute('aria-expanded', 'true');
        collapseToggleAll.textContent = 'Collapse All Groups';
      });

  // Using event delegation pattern here to avoid re-creating listeners each time DOM is modified.
  document.addEventListener('click', onClick);
  document.addEventListener('hidden.bs.collapse', onHiddenBsCollapse);
  document.addEventListener('shown.bs.collapse', onShownBsCollapse);

  return () => {
    document.removeEventListener('click', onClick);
    document.removeEventListener('hidden.bs.collapse', onHiddenBsCollapse);
    document.removeEventListener('shown.bs.collapse', onShownBsCollapse);
  };
};
