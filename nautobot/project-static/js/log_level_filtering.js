// Log Level Interface filtering
$('input.log-filter').on('input', function() {
    let filter = new RegExp(this.value);
    let log;

    for (log of $('table#logs > tbody > tr')) {
        if (filter.test(log.getAttribute('data-name'))) {
            $(log).show();
        } else {
            $(log).hide();
        }
    }
});
