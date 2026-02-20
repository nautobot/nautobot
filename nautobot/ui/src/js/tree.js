import htmx from 'htmx.org';

const collapseSubtree = (event) => {
  const ancestorsCount = event.target.closest('td').getElementsByClassName('nb-subtree').length;
  const tr = event.target.closest('tr');
  const url = new URL(window.location.href);
  while (tr.nextElementSibling?.querySelectorAll('.nb-tree-element .nb-subtree').length > ancestorsCount) {
    url.searchParams.delete(
      'expanded_subtree',
      tr.nextElementSibling.getElementsByClassName('nb-tree-element')[0].getAttribute('data-pk'),
    );
    tr.nextElementSibling.remove();
  }
  event.target.classList.toggle('nb-subtree-expanded', false);
  event.target.setAttribute('hx-get', event.target.getAttribute('_hx-get'));
  htmx.process(event.target);
  url.searchParams.delete('expanded_subtree', event.target.closest('td').getAttribute('data-pk'));
  window.history.replaceState(null, '', url);
};

const afterSubtreeExpansion = (span, addExpandedPrefix) => {
  span.classList.toggle('nb-subtree-expanded', true);
  span.setAttribute('_hx-get', span.getAttribute('hx-get'));
  span.removeAttribute('hx-get');
  htmx.process(span);
  span.addEventListener('click', collapseSubtree);
  if (addExpandedPrefix) {
    const url = new URL(window.location.href);
    url.searchParams.delete('expanded_subtree', span.closest('td').getAttribute('data-pk')); // Avoid dupes
    url.searchParams.append('expanded_subtree', span.closest('td').getAttribute('data-pk'));
    window.history.replaceState(null, '', url);
  }
};

const maybeAddSubtreeExpansionCaret = (td) => {
  const ancestorsCount = td.getElementsByClassName('nb-subtree').length;
  const carets = td.getElementsByClassName('nb-subtree-expandable');
  if (carets.length > 0) {
    const [caret] = carets;
    caret.setAttribute('hx-on:htmx:after-on-load', 'window.nb.afterSubtreeExpansion(this, true)');
    const tr = td.closest('tr');
    if (tr.nextElementSibling?.querySelectorAll('.nb-tree-element .nb-subtree').length > ancestorsCount) {
      // Already expanded to show subtree
      afterSubtreeExpansion(caret, false);
    }
  }
};

const fixupSubtreeDisplay = (td) => {
  const subtreeElements = Array.from(td.getElementsByClassName('nb-subtree'));
  const currentDepth = subtreeElements.length;
  const tr = td.closest('tr');

  subtreeElements.slice(0, -2).forEach((element, index) => {
    let nextTr = tr.nextElementSibling;
    while (nextTr?.querySelectorAll('.nb-tree-element .nb-subtree').length > index + 2) {
      nextTr = nextTr.nextElementSibling;
    }
    if (!nextTr || nextTr.querySelectorAll('.nb-tree-element .nb-subtree').length === index + 2) {
      element.classList.toggle('nb-subtree-ancestor-next-sibling', true);
    } else {
      element.classList.toggle('nb-subtree-ancestor-no-next-sibling', true);
    }
  });

  const lastElement = subtreeElements.at(-2);
  if (lastElement) {
    let nextTr = tr.nextElementSibling;
    while (nextTr?.querySelectorAll('.nb-tree-element .nb-subtree').length > currentDepth) {
      nextTr = nextTr.nextElementSibling;
    }
    if (!nextTr || nextTr.querySelectorAll('.nb-tree-element .nb-subtree').length === currentDepth) {
      lastElement.classList.toggle('nb-subtree-next-sibling', true);
    } else {
      lastElement.classList.toggle('nb-subtree-no-next-sibling', true);
    }
  }
};

export const initializeSubtrees = () => {
  htmx.onLoad((content) => {
    const tree_tds = Array.from(content.getElementsByClassName('nb-tree-element'));
    if (tree_tds.length > 0) {
      tree_tds.forEach((td) => {
        maybeAddSubtreeExpansionCaret(td);
        fixupSubtreeDisplay(td);
      });
      htmx.process(content);

      const urlParams = new URLSearchParams(window.location.search);
      urlParams.getAll('expanded_subtree').forEach((pk) => {
        htmx.find(`td[data-pk="${pk}"] .nb-subtree-expandable:not(.nb-subtree-expanded)`)?.click();
      });
    }
  });

  window.nb.afterSubtreeExpansion = afterSubtreeExpansion;
};
