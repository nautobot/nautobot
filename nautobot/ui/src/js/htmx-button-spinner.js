// Class string for the spinner. Kept in sync with Nautobot's canonical icon markup
// (`mdi ...` + `aria-hidden`) so it can be applied by swapping an existing icon's classes.
const SPINNER_CLASS = 'mdi spinner-border spinner-border-sm';

/**
 * Show a loading spinner on a `.btn` element while it issues an HTMX request.
 *
 * HTMX requests are XHR-based and never trigger the browser's native loading indicator, so a click on an HTMX button
 * gives no feedback that the request is in flight. This adds that feedback globally: whenever an element that is itself
 * the HTMX requester (`event.detail.elt`) carries the `.btn` class, a Bootstrap spinner is shown for the duration of
 * the request and removed when it completes (success or failure).
 *
 * If the button has a leading MDI icon, the icon's classes are temporarily swapped for the spinner; otherwise a spinner
 * is prepended before the label. The original state is tracked via `data-nb-*` attributes so it can be restored.
 *
 * Only elements that are themselves the requester and are `.btn` are affected -- paginator links, tree carets, the
 * sidenav favorites toggle (none are `.btn`) and non-HTMX buttons are left untouched. Submit buttons inside HTMX forms
 * are not covered, because the request fires on the `<form>`, not the button.
 * @returns {void} Do not return any value, attach event listeners.
 */
export const initializeHtmxButtonSpinner = () => {
  const onBeforeRequest = (event) => {
    const button = event.detail?.elt;
    if (!(button instanceof HTMLElement) || !button.classList.contains('btn')) {
      return;
    }
    if (button.dataset.nbSpinnerActive) {
      return; // A spinner is already showing for an in-flight request on this button.
    }

    const icon = button.querySelector('.mdi');
    if (icon) {
      // Temporarily replace the existing icon by swapping its classes; restored on completion.
      button.dataset.nbSpinnerIconClass = icon.className;
      icon.className = SPINNER_CLASS;
      button.dataset.nbSpinnerActive = 'icon';
    } else {
      // No icon: prepend a spinner (plus a trailing space) before the label.
      const spinner = document.createElement('span');
      spinner.className = SPINNER_CLASS;
      spinner.setAttribute('aria-hidden', 'true');
      spinner.dataset.nbInjectedSpinner = 'true';
      button.insertBefore(spinner, button.firstChild);
      spinner.after(' ');
      button.dataset.nbSpinnerActive = 'injected';
    }
  };

  const onAfterRequest = (event) => {
    const button = event.detail?.elt;
    const mode = button?.dataset?.nbSpinnerActive;
    if (!mode) {
      return;
    }

    if (mode === 'icon') {
      const icon = button.querySelector('.mdi');
      if (icon) {
        icon.className = button.dataset.nbSpinnerIconClass;
      }
      delete button.dataset.nbSpinnerIconClass;
    } else {
      const spinner = button.querySelector('[data-nb-injected-spinner]');
      if (spinner) {
        const trailingSpace = spinner.nextSibling;
        if (trailingSpace?.nodeType === Node.TEXT_NODE && !trailingSpace.textContent.trim()) {
          trailingSpace.remove();
        }
        spinner.remove();
      }
    }

    delete button.dataset.nbSpinnerActive;
  };

  // Body-level delegation catches every HTMX request; matches the pattern in `modal.js`.
  document.body.addEventListener('htmx:beforeRequest', onBeforeRequest);
  document.body.addEventListener('htmx:afterRequest', onAfterRequest);
};
