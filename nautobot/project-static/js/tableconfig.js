$(document).ready(function() {
    $('form.userconfigform input.reset').click(function(event) {
        // Deselect all columns when the reset button is clicked
        $('select[name="columns"]').val([]);
    });

    $('form.userconfigform').submit(function(event) {
        event.preventDefault();

        // Derive an array from the dotted path to the config root
        let path = this.getAttribute('data-config-root').split('.');
        let data = {};
        let pointer = data;

        // Construct a nested JSON object from the path
        let node;
        for (node of path) {
            pointer[node] = {};
            pointer = pointer[node];
        }

        // Assign the form data to the child node
        let field;
        $.each($(this).find('[id^="id_"]:input'), function(index, value) {
            field = $(value);
            pointer[field.attr("name")] = field.val();
        });

        // Make the REST API request
        $.ajax({
            url: nautobot_api_path + 'users/config/',
            async: true,
            contentType: 'application/json',
            dataType: 'json',
            type: 'PATCH',
            beforeSend: function(xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", nautobot_csrf_token);
            },
            data: JSON.stringify(data),
        }).done(function () {
            // Reload the page
            if (window.location.href.includes("saved_view=")){
                var new_url = window.location.href+"&table_changes_pending=true";
                window.location.assign(new_url);
            } else {
                window.location.reload(true);
            }
        }).fail(function (xhr, status, error) {
            alert("Failed to update user config (" + status + "): " + error);
        });
    });
});
