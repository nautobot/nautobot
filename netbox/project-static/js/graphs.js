$('#graphs_modal').on('show.bs.modal', function (event) {
    var button = $(event.relatedTarget);
    var obj = button.data('obj');
    var url = button.data('url');
    var modal_title = $(this).find('.modal-title');
    var modal_body = $(this).find('.modal-body');
    modal_title.text(obj);
    modal_body.empty();
    $.ajax({
        url: url,
        dataType: 'json',
        success: function(json) {
            $.each(json, function(i, graph) {
                // Build in a 500ms delay per graph to avoid hammering the server
                setTimeout(function() {
                    modal_body.append('<h4 class="text-center">' + graph.name + '</h4>');
                    if (graph.embed_link) {
                        modal_body.append('<a href="' + graph.embed_link + '"><img src="' + graph.embed_url + '" /></a>');
                    } else {
                        modal_body.append('<img src="' + graph.embed_url + '" />');
                    }
                }, i*500);
            })
        }
    });
});
