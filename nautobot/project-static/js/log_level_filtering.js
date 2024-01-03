
document.querySelector('input#log-filter').addEventListener('input', function() {
    qs = `?q=${this.value}`
    updateLogTable(job_result_id, qs)
});

