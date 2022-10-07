// Log level and message filtering
$('input.log-filter').on('input keydown', function(ev) {

    // Ignore the return key to prevent form submission
    if(ev.keyCode === 13) {
        return false;
    }

    let filter = new RegExp(this.value);
    let log;

    // Get column indexes in order to extract required cell data in the coming for loop
    let logLevelColumn = $('table#logs > thead > tr > th:contains("Level")').index();
    let messageColumn = $('table#logs > thead > tr > th:contains("Message")').index();

    for (log of $('table#logs > tbody > tr')) {

        // Get text values from log level and message cells
        // NB: .text() strips all html tags, leaving us with plain innerText
        let logLevel = $(log).find('td').eq(logLevelColumn).text();
        let message = $(log).find('td').eq(messageColumn).text();

        // Perform a regex test on the log level and message column text
        if (filter.test(logLevel) || filter.test(message)) {
            $(log).show();
        } else {
            $(log).hide();
        }
    }
});
