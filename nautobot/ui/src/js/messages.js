/*  eslint-disable no-underscore-dangle */

import * as bootstrap from 'bootstrap';
import htmx from 'htmx.org';

const REFRESH_MESSAGES_INTERVAL = 15000;

const TOAST_CLASS = 'toast';
const TOAST_CONTAINER_CLASS = 'toast-container';
const TOAST_MESSAGES_ID = 'toast-messages';
const TOAST_TIMEOUT_INDICATOR_CLASS = 'nb-toast-timeout-indicator';

/*
 * `toasts` keeps track of initialized toasts, also storing their destructor functions and timeout indicator running
 * statuses. Technically, it could be a simple object, but since this collection is undergoing mutations over time,
 * `Map` has more convenient API suited for these kinds of operations, such as `has`, `set`, and `delete` methods. It is
 * shared by all `initializeToasts` calls, so that repeated calls cannot initialize the same toast twice.
 */
const toasts = new Map();

/**
 * Get Bootstrap `Toast` instance.
 * @param {string} id - Toast HTML element identifier.
 * @returns {(bootstrap.Toast|null)} Bootstrap `Toast` instance, if it exists, `null` otherwise.
 */
const getToastInstance = (id) => bootstrap.Toast.getInstance(document.getElementById(id));

/**
 * Initialize toast timeout indicator, i.e. toast close countdown bar at the bottom of `autohide` toast elements.
 * @param {string} id - Toast HTML element identifier.
 * @returns {(function(): void)} Destructor function that effectively reverts toast timeout indicator initialization.
 */
const initializeToastTimeoutIndicator = (id) => {
  const getTimeoutIndicator = () => document.querySelector(`#${CSS.escape(id)} .${TOAST_TIMEOUT_INDICATOR_CLASS}`);
  const setIsTimeoutIndicatorRunning = (isTimeoutIndicatorRunning) =>
    toasts.set(id, { ...toasts.get(id), isTimeoutIndicatorRunning });

  // `run` toast timeout indicator.
  const run = () => {
    const instance = getToastInstance(id);
    const delay = instance?._config?.delay;
    const timeout = instance?._timeout;

    // If there is no `_timeout`, the toast closing is not yet scheduled, so timeout indicator should not run either.
    if (timeout !== undefined && timeout !== null) {
      const indicator = getTimeoutIndicator();

      if (indicator) {
        setIsTimeoutIndicatorRunning(true);

        /*
         * Standard RAF (`requestAnimationFrame`) style animation which shrinks the timeout indicator `width` from
         * `100%` to `0` (or near-zero), over the course of `delay` milliseconds.
         */
        const start = { current: undefined };
        const shrink = (time) => {
          start.current ??= time;
          const elapsed = time - start.current;
          if (elapsed < delay && indicator && toasts.get(id)?.isTimeoutIndicatorRunning) {
            indicator.style.setProperty('width', `${100 - (elapsed / delay) * 100}%`);
            window.requestAnimationFrame(shrink);
          } else {
            setIsTimeoutIndicatorRunning(false);
          }
        };

        window.requestAnimationFrame(shrink);
      }
    }
  };

  // Reset timeout indicator - stop it if its running and revert its `width` to the default style.
  const reset = () => {
    const indicator = getTimeoutIndicator();

    if (indicator) {
      indicator.style.removeProperty('width');
      setIsTimeoutIndicatorRunning(false);
    }
  };

  run();

  /*
   * This is arguably the trickiest and dirtiest part of the toast timeout indicators implementation, which requires
   * overloading private Bootstrap `Toast` instance methods. While Bootstrap exposes some toast methods and events, they
   * are insufficient to get any readings of toast closing countdown from the outside. On the flip side, said overloads
   * only involve calling original Bootstrap functions followed by Nautobot custom functions, so they do not alter the
   * underlying implementation, but rather extend it.
   */
  const instance = getToastInstance(id);
  const originalMaybeScheduleHide = instance._maybeScheduleHide;
  instance._maybeScheduleHide = () => {
    originalMaybeScheduleHide.call(instance);
    run();
  };

  const originalClearTimeout = instance._clearTimeout;
  instance._clearTimeout = () => {
    originalClearTimeout.call(instance);
    reset();
  };

  return () => {
    const instanceToBeDestroyed = getToastInstance(id);

    if (instanceToBeDestroyed) {
      instanceToBeDestroyed._maybeScheduleHide = originalMaybeScheduleHide;
      instanceToBeDestroyed._clearTimeout = originalClearTimeout;
    }

    reset();
  };
};

/**
 * Initialize all toasts on the page, and watch the toast containers for any toast additions or removals. Note that
 * duplicate initializations are prevented, so this function is safe to be called multiple times if needed.
 * @returns {(function(): void)} Destructor function that effectively reverts toasts initialization.
 */
export const initializeToasts = () => {
  // Initialize `toast` HTML element.
  const initialize = (toast) => {
    const generateUniqueToastId = (count = 0) => {
      const id = `toast_${count}`;
      return document.getElementById(id) || toasts.has(id) ? generateUniqueToastId(count + 1) : id;
    };
    // Ensure that every toast has a unique `id`. If the `id` is missing, generate one.
    const id = toast.getAttribute('id') || generateUniqueToastId();
    toast.setAttribute('id', id);

    // Skip toast initialization if it already has been initialized.
    if (!toasts.has(id)) {
      const instance = bootstrap.Toast.getOrCreateInstance(toast);
      const destroyToastTimeoutIndicator = initializeToastTimeoutIndicator(id);

      toasts.set(id, {
        isTimeoutIndicatorRunning: false,
        ...toasts.get(id),
        destructor: () => {
          /*
           * Circumstances on the page may change between toast initialization and destruction, so instead of keeping
           * element and instance references within closures, prefer referencing toasts by their `id`s.
           */
          destroyToastTimeoutIndicator();
          getToastInstance(id)?.dispose();
          toasts.delete(id);
        },
      });

      if (!instance.isShown()) {
        instance.show();
      }
    }
  };

  // Iterate over and initialize all toasts on the page.
  document.querySelectorAll(`.${TOAST_CLASS}`).forEach((toast) => initialize(toast));

  // Watch toast containers for any toast additions or removals, initializing and destructing toasts when applicable.
  const observer = new MutationObserver((mutations) =>
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node instanceof Element && node.classList.contains(TOAST_CLASS)) {
          initialize(node);
        }
      });
      mutation.removedNodes.forEach((node) => toasts.get(node.getAttribute?.('id'))?.destructor());
    }),
  );
  document
    .querySelectorAll(`#${TOAST_MESSAGES_ID}, .${TOAST_CONTAINER_CLASS}`)
    .forEach((container) => observer.observe(container, { childList: true }));

  return () => {
    [...toasts].forEach(([, { destructor }]) => destructor());
    observer.disconnect();
  };
};

/**
 * Refresh Django messages on the page using HTMX swap.
 * @param {string} url - HTMX AJAX request URL, it should always be `'{% url "messages" %}'`. The quirk of always
 *   requiring the function caller to pass the same URL argument comes from the fact that JavaScript UI cannot use
 *   Django APIs such as `{% url %}` template tag in this case.
 * @returns {Promise<void>} Promise resolved when HTMX AJAX request finishes.
 */
export const refreshMessages = (url) =>
  htmx.ajax('GET', url, {
    select: '#header_messages > *',
    selectOOB: `#${TOAST_MESSAGES_ID}:beforeend`,
    swap: 'beforeend',
    target: '#header_messages',
  });

/**
 * Watch for new Django messages, refreshing them periodically.
 * @param {string} url - HTMX AJAX request URL, passed through to `refreshMessages`, see its documentation for why the
 *   caller always has to provide it.
 * @returns {(function(): void)} Destructor function that stops watching for new messages.
 */
export const watchMessages = (url) => {
  const timeout = { current: undefined };

  const watch = () => {
    timeout.current = setTimeout(async () => {
      // Refresh messages only if browser tab is active, otherwise just keep an idle loop alive.
      if (!document.hidden) {
        try {
          await refreshMessages(url);
        } catch {
          // Refresh failures are transient, so they are ignored to keep a single one from stopping the loop.
        }
      }
      watch();
    }, REFRESH_MESSAGES_INTERVAL);
  };

  watch();

  return () => clearTimeout(timeout.current);
};
