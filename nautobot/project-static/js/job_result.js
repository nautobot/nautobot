var url = nautobot_api_path + "extras/job-results/";
var timeout = 1000;
var terminal_statuses = ['completed', 'failed', 'errored'];
var session_key = "ajax_table_current_page";

function updatePendingStatusLabel(status) {
    // Updates "Status" label in "Summary of Results" table in JobResult detail view.
    var labelClass;
    if (status.value === 'failed' || status.value === 'errored') {
        labelClass = 'danger';
    }
    else if (status.value === 'running') {
        labelClass = 'warning';
    }
    else if (status.value === 'completed') {
        labelClass = 'success';
    }
    else {
        labelClass = 'default';
    }
    var elem = $('#pending-result-label > label');
    elem.attr('class', 'label label-' + labelClass);
    elem.text(status.label);
}

function updateLogTable(result_id) {
    // Calls `update_log_table` to refresh the jobs table from the `/log-table/` endpoint
    // Grab the query string from session storage and pass it through to the log table.
    let qs = window.sessionStorage.getItem(session_key) || "";
    update_log_table(qs, '/extras/job-results/' + result_id + '/log-table/');
}

$(document).ready(function(){
    if (pending_result_id !== null) {
        (function checkPendingResult() {
            // Keep checking results, update the table, and refresh the logs. When done, refresh the
            // page to finalize the job results output.
            $.ajax({
                url: url + pending_result_id + '/',
                method: 'GET',
                dataType: 'json',
                context: this,
                success: function(data) {
                    // Update the status label
                    updatePendingStatusLabel(data.status);

                    // Update the job logs table
                    updateLogTable(pending_result_id);

                    /// Should reload the page yet?
                    let reload_page = window.sessionStorage.getItem(session_key) == null;

                    // If there is a terminal status, refresh the page and clear session storage.
                    if (terminal_statuses.includes(data.status.value)) {
                        window.sessionStorage.removeItem(session_key);
                        reload_page && window.location.reload();
                    }
                    // Otherwise call myself again after `timeout`.
                    else {
                        setTimeout(checkPendingResult, timeout);
                        // Back off each iteration, until we reach a 10s interval.
                        if (timeout < 10000) {
                            timeout += 1000
                        }
                    }
                }
            });
        })();
    }
})
