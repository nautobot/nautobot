// Global handler for the shared `#nautobot-generic-modal` used by job modal buttons
// and other HTMX-driven modals. This lives in global JS (rather than in
// `generic/object_retrieve.html`) so that list views and other non-detail views
// also trigger the reload-on-close behavior and the content reset.
document.addEventListener('hidden.bs.modal', function (event) {
    if (event.target.id !== 'nautobot-generic-modal') {
        return;
    }
    const container = document.getElementById('modal-content-container');
    if (!container) {
        return;
    }

    // If the modal content opted in to refreshing the page when the
    // associated Job has completed, reload before resetting content.
    if (container.querySelector('[data-refresh-on-close="true"]')) {
        window.location.reload();
        return;
    }

    // Restore the fallback HTML, this will reset the modal, ensuring that any HTMX state is cleared
    // and the loading spinner is shown for the next use.
    container.innerHTML = `
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
});
