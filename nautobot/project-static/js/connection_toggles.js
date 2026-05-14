function setLabel(elem, icon, text) {
    elem.textContent = '';
    if (icon) {
        elem.appendChild(icon);
    }
    elem.appendChild(document.createTextNode(' ' + text));
}

function toggleConnection(elem) {
    const url = nautobot_api_path + "dcim/cables/" + elem.getAttribute('data') + "/";
    const isConnected = elem.classList.contains('connected');
    const newStatus = isConnected ? 'Planned' : 'Connected';

    fetch(url, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CSRFToken': nautobot_csrf_token,
        },
        body: JSON.stringify({status: newStatus}),
    }).then(function(response) {
        if (!response.ok) {
            return;
        }
        const row = elem.closest('tr');
        const icon = elem.querySelector(':scope > span');
        if (isConnected) {
            if (row) {
                row.classList.remove('table-success');
                row.classList.add('table-info');
            }
            elem.classList.remove('connected', 'text-warning');
            elem.classList.add('text-success');
            if (icon) {
                icon.classList.remove('mdi-lan-pending');
                icon.classList.add('mdi-lan-connect');
            }
            setLabel(elem, icon, 'Mark cable as Connected');
        } else {
            if (row) {
                row.classList.remove('table-info');
                row.classList.add('table-success');
            }
            elem.classList.remove('text-success');
            elem.classList.add('connected', 'text-warning');
            if (icon) {
                icon.classList.remove('mdi-lan-connect');
                icon.classList.add('mdi-lan-pending');
            }
            setLabel(elem, icon, 'Mark cable as Planned');
        }
    });
    return false;
}

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.cable-toggle').forEach(function(elem) {
        elem.addEventListener('click', function(event) {
            event.preventDefault();
            toggleConnection(elem);
        });
    });
});
