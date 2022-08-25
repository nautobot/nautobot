// Log Level Interface filtering
$('input.log-filter').on('input keydown', function(ev) {
    // ignore return key
    if(ev.keyCode === 13) {
        return false;
    }
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
