function setLabel(elem, icon, text) {
    elem.textContent = '';
    if (icon) {
        elem.appendChild(icon);
    }
    elem.append(text);
}

function toggleConnection(elem) {
    const url = nautobot_api_path + "dcim/cables/" + elem.getAttribute('data') + "/";
    const wasConnected = elem.classList.contains('connected');
    const oldStatus = wasConnected ? 'Connected' : 'Planned';
    const newStatus = wasConnected ? 'Planned' : 'Connected';

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
        if (row) {
            row.classList.toggle('table-success', newStatus === 'Connected');
            row.classList.toggle('table-info', newStatus === 'Planned');
        }
        elem.classList.toggle('connected', newStatus === 'Connected');
        elem.classList.toggle('text-warning', newStatus === 'Connected');
        elem.classList.toggle('text-success', newStatus === 'Planned');
        if (icon) {
            icon.classList.toggle('mdi-lan-connect', newStatus === 'Planned');
            icon.classList.toggle('mdi-lan-pending', newStatus === 'Connected');
        }
        setLabel(elem, icon, `Mark cable as ${oldStatus}`);
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
