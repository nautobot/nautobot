function setLabel(elem, icon, text) {
    elem.textContent = '';
    if (icon) {
        elem.appendChild(icon);
    }
    elem.append(text);
}

function changeCableTerminationColors(cablePk, newStatus) {
    if (!cablePk) {
        return;
    }

    const cableRows = document.querySelectorAll(`tr[data-cable-pk="${cablePk}"]`);
    cableRows.forEach(function(cableRow) {
        cableRow.classList.remove('table-success', 'table-info', 'table-warning');
        cableRow.classList.add(newStatus === 'Connected' ? 'table-success' : 'table-info');
    });
}

function changeCableTerminationToggleButtons(cablePk, newStatus) {
    if (!cablePk) {
        return;
    }

    const nextAction = newStatus === 'Connected' ? 'Planned' : 'Connected';
    const toggles = document.querySelectorAll(`a.cable-toggle[data="${cablePk}"]`);
    toggles.forEach(function(toggle) {
        const icon = toggle.querySelector(':scope > span');
        toggle.classList.toggle('connected', newStatus === 'Connected');
        toggle.classList.toggle('text-warning', newStatus === 'Connected');
        toggle.classList.toggle('text-success', newStatus === 'Planned');
        if (icon) {
            icon.classList.toggle('mdi-lan-connect', newStatus === 'Planned');
            icon.classList.toggle('mdi-lan-pending', newStatus === 'Connected');
        }
        setLabel(toggle, icon, `Mark cable as ${nextAction}`);
    });
}

function toggleConnection(elem) {
    const cablePk = elem.getAttribute('data');
    const url = nautobot_api_path + "dcim/cables/" + cablePk + "/";
    const wasConnected = elem.classList.contains('connected');
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

        changeCableTerminationColors(cablePk, newStatus);
        changeCableTerminationToggleButtons(cablePk, newStatus);
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
