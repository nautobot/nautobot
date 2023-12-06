// Enables panels on homepage to be collapsed and expanded
document.addEventListener('DOMContentLoaded', function() {
    // Function to toggle and save state for a specific collapsible element
    function toggleAndSaveState(elementId) {
        // Remove 'toggle-' in the ID to get the localStorage key the toggle btn references
        elementId = elementId.replace("toggle-", "");
        var collapsibleDiv = document.getElementById(elementId);

        // Toggle the collapsed class
        if (collapsibleDiv.classList.contains('collapsed')) {
            collapsibleDiv.classList.remove('collapsed');
        } else {
            collapsibleDiv.classList.add('collapsed');
        }

        // Update the state in localStorage
        var isCollapsed = collapsibleDiv.classList.contains('in');
        localStorage.setItem(elementId, isCollapsed ? 'collapsed' : 'expanded');
        // Set Cookie value based on isCollapsed
        if (isCollapsed) {
            document.cookie = elementId + "=True; path=/";
        } else {
            document.cookie = elementId + "=False; path=/";
        }
    }

    // Add event listener to each collapsible div
    var collapseIcons = document.querySelectorAll('.collapse-icon');
    collapseIcons.forEach(function(icon) {
        icon.addEventListener('click', function() {
            var elementId = this.id;
            toggleAndSaveState(elementId);
        });
    });
});

// Enables panels on homepage to be rearranged via drag and drop
$(document).ready(function() {
    // Initialize draggable and sortable
    $("#draggable-homepage-panels").sortable({
        update: function(event, ui) {
            savePanelOrder();
        }
    });

    // Load saved panel order on page load
    loadSavedPanelOrder();

    // Function to save the order of panels in localStorage
    function savePanelOrder() {
        var panelOrder = $("#draggable-homepage-panels").sortable("toArray");
        localStorage.setItem("homepage-panels-order", JSON.stringify(panelOrder));
    }

    // Function to load the saved order of panels from localStorage
    function loadSavedPanelOrder() {
        var savedOrder = localStorage.getItem("homepage-panels-order");

        if (savedOrder) {
            savedOrder = JSON.parse(savedOrder);
            
            for (var i = 0; i < savedOrder.length; i++) {
                $("#" + savedOrder[i]).appendTo("#draggable-homepage-panels");
            }
        }
        $("#draggable-homepage-panels").fadeIn("slow");
    }
});
