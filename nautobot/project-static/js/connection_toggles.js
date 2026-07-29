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

function disconnectTermination(elem) {
    // Detach a single termination from its cable. The post_delete signal handler on
    // CableToCableTermination rebuilds affected CablePaths.
    fetch(nautobot_api_path + "dcim/cables-to-cable-terminations/" + elem.getAttribute('data') + "/", {
        method: 'DELETE',
        headers: {
            'Accept': 'application/json',
            'X-CSRFToken': nautobot_csrf_token,
        },
    }).then(function(response) {
        if (response.ok) {
            window.location.reload();
        }
    });
    return false;
}

// Delegate from `document` rather than binding each `.cable-toggle`/`.cable-disconnect` element
// directly: object-list tables (and UIViewSet list views) render their rows via HTMX, replacing
// the table after page load, so per-element listeners bound on `DOMContentLoaded` would be lost on
// every swap. A single delegated listener keeps working for swapped-in rows. (Matches the
// delegation pattern already used in cable_update.html and generic/object_list.html.)
document.addEventListener('click', function(event) {
    const toggle = event.target.closest('.cable-toggle');
    if (toggle) {
        event.preventDefault();
        toggleConnection(toggle);
        return;
    }
    const disconnect = event.target.closest('.cable-disconnect');
    if (disconnect) {
        event.preventDefault();
        disconnectTermination(disconnect);
    }
});
