$(document).ready(function() {
    var search_field = $('#id_livesearch');
    var search_key = search_field.attr('data-key');
    var label = search_field.attr('data-label');
    if (!label) {
        label = 'name';
    }

    search_field.autocomplete({
        source: function(request, response) {
            $.ajax({
                type: 'GET',
                url: search_field.attr('data-source'),
                data: search_key + '=' + request.term,
                success: function(data) {
                    var choices = [];
                    $.each(data, function (index, choice) {
                        choices.push({
                            value: choice.id,
                            label: choice[label]
                        });
                    });
                    response(choices);
                }
            });
        },
        select: function(event, ui) {
            event.preventDefault();
            search_field.val(ui.item.label);
            var real_field = $('#id_' + search_field.attr('data-field'));
            real_field.empty();
            real_field.append($("<option></option>").attr('value', ui.item.value).text(ui.item.label));
            real_field.change();
            // If the field has a parent helper, reset the parent to no selection
            $('select[filter-for="' + real_field.attr('name') + '"]').val('');
        },
        minLength: 4,
        delay: 500
    });
});
