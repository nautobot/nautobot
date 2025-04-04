function toggleConnection(elem) {
    var url = nautobot_api_path + "dcim/cables/" + elem.attr('data') + "/";
    elem.tooltip("destroy");
    if (elem.hasClass('connected')) {
        $.ajax({
            url: url,
            method: 'PATCH',
            contentType: "application/json",
            dataType: 'json',
            beforeSend: function(xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", nautobot_csrf_token);
            },
            data: JSON.stringify({'status': 'Planned'}),
            context: this,
            success: function() {
                elem.parents('tr').removeClass('success').addClass('info');
                elem.removeClass('connected btn-warning').addClass('btn-success');
                elem.attr('title', 'Mark installed');
                elem.children('i').removeClass('mdi mdi-lan-disconnect').addClass('mdi mdi-lan-connect')
                elem.tooltip("show");
            }
        });
    } else {
        $.ajax({
            url: url,
            method: 'PATCH',
            contentType: "application/json",
            dataType: 'json',
            beforeSend: function(xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", nautobot_csrf_token);
            },
            data: JSON.stringify({'status': 'Connected'}),
            context: this,
            success: function() {
                elem.parents('tr').removeClass('info').addClass('success');
                elem.removeClass('btn-success').addClass('connected btn-warning');
                elem.attr('title', 'Mark planned');
                elem.children('i').removeClass('mdi mdi-lan-connect').addClass('mdi mdi-lan-disconnect')
                elem.tooltip("show");
            }
        });
    }
    return false;
}
$(".cable-toggle").click(function() {
    return toggleConnection($(this));
});
