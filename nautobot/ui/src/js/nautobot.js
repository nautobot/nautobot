/* eslint import/order: ['error', { alphabetize: { order: 'asc' }, 'newlines-between': 'ignore' }] */

import '../scss/nautobot.scss';

import * as bootstrap from 'bootstrap';
window.bootstrap = bootstrap;

import ClipboardJS from 'clipboard';
window.ClipboardJS = ClipboardJS;

import * as echarts from 'echarts';
window.echarts = echarts;

import flatpickr from 'flatpickr';
window.flatpickr = flatpickr;

import hljs from 'highlight.js/lib/core';
import graphql from 'highlight.js/lib/languages/graphql';
import json from 'highlight.js/lib/languages/json';
import xml from 'highlight.js/lib/languages/xml';
import yaml from 'highlight.js/lib/languages/yaml';

import htmx from 'htmx.org';
window.htmx = htmx;

hljs.registerLanguage('graphql', graphql);
hljs.registerLanguage('json', json);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('yaml', yaml);
window.hljs = hljs;

import jQuery from 'jquery';
window.jQuery = jQuery;
window.$ = window.jQuery;

import 'jquery-ui';
import 'jquery-ui/ui/widgets/sortable.js';
import 'select2';

import { initializeCheckboxes } from './checkbox.js';
import { initializeCollapseToggleAll } from './collapse.js';
import { initializeDraggable } from './draggable.js';
import { initializeDrawers } from './drawer.js';
import { observeFormStickyFooters } from './form.js';
import { loadState, saveState } from './history.js';
import { initializeSearch } from './search.js';
import { initializeSelect2Fields, setSelect2Value } from './select2.js';
import { initializeSidenav } from './sidenav.js';
import { observeCollapseTabs } from './tabs.js';
import { initializeTheme } from './theme.js';

document.addEventListener('DOMContentLoaded', () => {
  window.nb ??= {};

  // History
  loadState();
  window.nb.history = { saveState };

  // Tooltips
  // https://getbootstrap.com/docs/5.3/components/tooltips/#enable-tooltips
  [...document.querySelectorAll('[data-bs-toggle="tooltip"]')].forEach((tooltip) => new bootstrap.Tooltip(tooltip));

  // Sidenav
  initializeSidenav();

  // Checkbox
  window.nb.checkbox = { initializeCheckboxes };

  // Collapse
  initializeCollapseToggleAll();

  // Draggable
  initializeDraggable();

  // Drawer
  initializeDrawers();

  // Form
  // TODO(norbert-mieczkowski-codilime): for htmx SPA-like behavior, re-initialize sticky footers like tabs below.
  observeFormStickyFooters();

  // Search
  initializeSearch();

  // Select2
  window.nb.select2 = { initializeSelect2Fields, setSelect2Value };

  // Tabs
  /*
   * TODO(norbert-mieczkowski-codilime): listen for proper event type(s) to re-initialize collapse tabs observers when
   *   htmx dynamic content reloading is implemented. Said re-initialization should be as simple as something like:
   *   ```js
   *   let unobserveCollapseTabs = observeCollapseTabs();
   *   document.body.addEventListener('htmx:xhr:loadend', () => unobserveCollapseTabs());
   *   document.body.addEventListener('htmx:load', () => {
   *     unobserveCollapseTabs = observeCollapseTabs();
   *   });
   *   ```
   */
  observeCollapseTabs();

  // Theme
  initializeTheme();

  const toggleFavorite = (element, event) => {
    if (event.detail.successful) {
      element.classList.toggle('active');
    }
  };
  window.toggleFavorite = toggleFavorite;

  const setRequestUrl = (element, event) => {
    const isFavorite = element.classList.contains('active');
    event.detail.path = isFavorite ? element.dataset.deleteUrl : element.dataset.addUrl;
  };
  window.setRequestUrl = setRequestUrl;

  // Remove the blur after clicking the footer links that are opening mostly in the new tab
  // Keeping focus on those items is what keeps the tooltip as well
  document.querySelectorAll('a[data-bs-toggle="tooltip"], div[data-bs-toggle="tooltip"] > a').forEach((el) => {
    el.addEventListener('click', () => {
      el.blur();
    });
  });

  // When modal is being closed, bootstrap automatically restore the focus on the element that was triggering the modal
  // As a result, after modal close tooltip was triggered as well
  document.addEventListener('hidden.bs.modal', () => {
    document.querySelectorAll('[data-bs-toggle="tooltip"] > a').forEach((el) => {
      el.blur();
    });
  });
});
