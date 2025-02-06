function checkSecret() {
    $.ajax({
        url: "{% url 'extras-api:secret-check' pk=object.pk %}",
        dataType: 'json',
        success: function(json) {
            if(json.result) {
                alert("The secret was successfully retrieved.")
            } else {
                alert("Error retrieving secret: \n\n" + json.message)
            }
        },
        error: function(xhr) {
            alert("Error checking secret: \n\n" + xhr.responseText);
        }
    });
}
