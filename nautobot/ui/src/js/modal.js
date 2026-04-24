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

/**
 * Initialize behavior for the shared `#nautobot-generic-modal` used by job modal buttons and other HTMX-driven modals.
 * On close, optionally reloads the page when the modal content opted in via `data-refresh-on-close="true"`, otherwise
 * resets the modal content back to a loading fallback so the next open starts from a clean state.
 * @returns {void} Do not return any value, attach an event listener.
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
};
