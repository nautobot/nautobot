import { initializeSelect2Fields } from './select2.js';

const MODAL_ID = 'nautobot-generic-modal';
const MODAL_CONTENT_CONTAINER_ID = 'modal-content-container';
const REFRESH_ON_CLOSE_SELECTOR = '[data-nb-refresh-on-close="true"]';

// The heading id must match the modal's `aria-labelledby` in `inc/generic_modal.html` and `inc/modal_header.html`.
const FALLBACK_CONTENT = `
  <div class="modal-header">
    <h2 class="modal-title" id="nautobot-generic-modal-title">Loading...</h2>
    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
  </div>
  <div class="modal-body text-center p-5">
    <div class="spinner-border text-primary" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
    <p class="mt-2 text-muted">Please wait while we fetch the content...</p>
  </div>
`;

const isModalContentTarget = (event) => event.detail?.target?.id === MODAL_CONTENT_CONTAINER_ID;

const MODAL_TRANSITIONING_CLASS = 'nb-modal-transitioning';

/**
 * Prevent the background page from sliding sideways ("wiggle") when a modal opens or closes.
 *
 * The `<body>` transitions `padding-inline` to animate the sidenav/drawer slide. When a modal opens/closes Bootstrap
 * writes/removes an inline `padding-right` on `<body>` to compensate for the scrollbar it hides, and that change would
 * otherwise be animated by the same transition. We suppress the transition for the brief modal open/close window only,
 * so both the sidenav and drawer animations remain intact.
 *
 * `show`/`hide` fire before Bootstrap mutates the padding, so the class is in place in time. On `shown`/`hidden` the
 * padding is already at its final value; a forced reflow commits that value with the transition still disabled before
 * the class is removed, so re-enabling the transition never sees a pending change to animate.
 * @returns {void} Do not return any value, attach event listeners.
 */
const initializeModalWiggleFix = () => {
  const forceReflow = (element) => element.offsetWidth; // Reading a layout property forces a synchronous reflow.
  const disable = () => document.body.classList.add(MODAL_TRANSITIONING_CLASS);
  const enable = () => {
    // Commit the reset padding while the transition is still disabled, so re-enabling it sees no pending change.
    forceReflow(document.body);
    document.body.classList.remove(MODAL_TRANSITIONING_CLASS);
  };

  document.addEventListener('show.bs.modal', disable);
  document.addEventListener('hide.bs.modal', disable);
  document.addEventListener('shown.bs.modal', enable);
  document.addEventListener('hidden.bs.modal', enable);
};

/**
 * Initialize behavior for the shared `#nautobot-generic-modal` used by job modal buttons and other HTMX-driven modals.
 * On close, optionally reloads the page when the modal content opted in via `data-nb-refresh-on-close="true"`, otherwise
 * resets the modal content back to a loading fallback so the next open starts from a clean state. Also re-initializes
 * Select2 fields after HTMX swaps into the modal, and renders an error message inside the modal on HTMX errors.
 * @returns {void} Do not return any value, attach event listeners.
 */
export const initializeModal = () => {
  initializeModalWiggleFix();

  document.addEventListener('hidden.bs.modal', (event) => {
    if (event.target.id !== MODAL_ID) {
      return;
    }

    const container = document.getElementById(MODAL_CONTENT_CONTAINER_ID);
    if (!container) {
      return;
    }

    if (container.querySelector(REFRESH_ON_CLOSE_SELECTOR)) {
      window.location.reload();
      return;
    }

    container.innerHTML = FALLBACK_CONTENT;
  });

  document.body.addEventListener('htmx:afterSwap', (event) => {
    if (!isModalContentTarget(event)) {
      return;
    }
    initializeSelect2Fields(event.detail.target);
  });

  document.body.addEventListener('htmx:responseError', (event) => {
    if (!isModalContentTarget(event)) {
      return;
    }
    const modalBody = document.querySelector(`#${MODAL_ID} .modal-body`);
    const modalTitle = document.querySelector(`#${MODAL_ID} .modal-title`);
    if (modalTitle) {
      modalTitle.innerText = 'Error Occurred';
    }
    if (modalBody) {
      modalBody.innerHTML = `
        <div class="alert alert-danger">
          <p><strong>Failed to load content.</strong></p>
          <p>The server responded with status: ${event.detail.xhr.status}</p>
        </div>
      `;
    }
  });
};
