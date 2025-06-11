import '../scss/nautobot.scss';

import * as bootstrap from 'bootstrap';
window.bootstrap = bootstrap;

import ClipboardJS from 'clipboard';
window.ClipboardJS = ClipboardJS;

import flatpickr from 'flatpickr';
window.flatpickr = flatpickr;

import hljs from 'highlight.js/lib/core';
import 'highlight.js/styles/github.css';
import graphql from 'highlight.js/lib/languages/graphql';
import json from 'highlight.js/lib/languages/json';
import xml from 'highlight.js/lib/languages/xml';
import yaml from 'highlight.js/lib/languages/yaml';

hljs.registerLanguage('graphql', graphql);
hljs.registerLanguage('json', json);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('yaml', yaml);
window.hljs = hljs;

import jQuery from 'jquery';
window.jQuery = jQuery;
window.$ = window.jQuery;

import 'jquery-ui';
import 'select2';

import { initializeDraggable } from './draggable.js';
import { initializeDrawers } from './drawer.js';
import { initializeSearch } from './search.js';
import { observeCollapseTabs } from './tabs.js';

document.addEventListener('DOMContentLoaded', function () {
  // Tooltips
  // https://getbootstrap.com/docs/5.3/components/tooltips/#enable-tooltips
  [...document.querySelectorAll('[data-bs-toggle="tooltip"]')].forEach((tooltip) => new bootstrap.Tooltip(tooltip));

  // Sidenav
  document.querySelector('.sidenav-toggler').addEventListener('click', (event) => {
    const toggler = event.currentTarget;

    const controls = toggler.getAttribute('aria-controls');
    const expanded = toggler.getAttribute('aria-expanded') === 'true';

    toggler.setAttribute('aria-expanded', String(!expanded));

    const sidenav = document.getElementById(controls);
    sidenav.classList.toggle('sidenav-collapsed', expanded);
  });

  [...document.querySelectorAll('.sidenav-list-item')].forEach((sidenavListItem) => {
    sidenavListItem.addEventListener('click', () => {
      const controls = sidenavListItem.getAttribute('aria-controls');
      const expanded = sidenavListItem.getAttribute('aria-expanded') === 'true';

      sidenavListItem.setAttribute('aria-expanded', String(!expanded));

      const onClickDocument = (documentClickEvent) => {
        const { target: documentClickTarget } = documentClickEvent;
        const sidenavFlyout = document.getElementById(controls);

        const isClickOutside =
          !sidenavListItem.contains(documentClickTarget) && !sidenavFlyout.contains(documentClickTarget);

        if (isClickOutside) {
          sidenavListItem.setAttribute('aria-expanded', 'false');
          document.removeEventListener('click', onClickDocument);
        }
      };

      expanded
        ? document.removeEventListener('click', onClickDocument)
        : document.addEventListener('click', onClickDocument);
    });
  });

  // Draggable
  initializeDraggable();

  // Drawer
  initializeDrawers();

  // Search
  initializeSearch();

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
  let unobserveCollapseTabs = observeCollapseTabs();

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
});
