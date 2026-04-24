import { initializeSelect2Fields } from './select2.js';

const MODAL_ID = 'nautobot-generic-modal';
const MODAL_CONTENT_CONTAINER_ID = 'modal-content-container';
const REFRESH_ON_CLOSE_SELECTOR = '[data-refresh-on-close="true"]';

const FALLBACK_CONTENT = `
  <div class="modal-header">
    <h4 class="modal-title" id="modal-fallback-title">Loading...</h4>
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

/**
 * Initialize behavior for the shared `#nautobot-generic-modal` used by job modal buttons and other HTMX-driven modals.
 * On close, optionally reloads the page when the modal content opted in via `data-refresh-on-close="true"`, otherwise
 * resets the modal content back to a loading fallback so the next open starts from a clean state. Also re-initializes
 * Select2 fields after HTMX swaps into the modal, and renders an error message inside the modal on HTMX errors.
 * @returns {void} Do not return any value, attach event listeners.
 */
export const initializeModal = () => {
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
