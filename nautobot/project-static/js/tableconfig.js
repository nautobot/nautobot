document.addEventListener('DOMContentLoaded', function () {
    document.querySelector('form.userconfigform input.reset').addEventListener("click", (e) => {
        // Deselect all columns when the reset button is clicked
        document.querySelectorAll('select[name="columns"]').forEach(
            el => el.innerHTML = ""
        )
    });

    var config_form = document.querySelector('form.userconfigform')
    config_form.addEventListener("submit", (event) => {
        event.preventDefault();

        // Derive an array from the dotted path to the config root
        let path = config_form.getAttribute('data-config-root').split('.');
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
        document.querySelectorAll('[id^="id_"]').forEach((index, value) => {
            field = document.getElementById(index.getAttribute("id"));
            if (field.tagName === 'SELECT') {
                var selected = [];
                for (var option of field.options) {
                    if (option.selected) {
                        selected.push(option.value);
                    }
                }
                pointer[field.getAttribute("name")] = selected;
            } else {
                pointer[field.getAttribute("name")] = field.value;
            }
        });
        // console.log("jquery");
        // $.each($(this).find('[id^="id_"]:input'), function (index, value) {
        //     field = $(value);
        //     console.log(field);
        //     console.log(field.attr("name"));
        //     console.log(field.val())
        //     if (index == 10) {
        //         index.getAttribute("name");
        //     }
        //     pointer[field.attr("name")] = field.val();
        // });

        // Make the REST API request
        $.ajax({
            url: nautobot_api_path + 'users/config/',
            async: true,
            contentType: 'application/json',
            dataType: 'json',
            type: 'PATCH',
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", nautobot_csrf_token);
            },
            data: JSON.stringify(data),
        }).done(function () {
            // Reload the page
            window.location.reload(true);
        }).fail(function (xhr, status, error) {
            alert("Failed to update user config (" + status + "): " + error);
        });
    });
});
