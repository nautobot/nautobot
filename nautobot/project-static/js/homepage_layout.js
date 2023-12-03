$(document).ready(function() {
    // Function to toggle and save state for a specific collapsible element
    function toggleAndSaveState(elementId) {
        // Remove 'toggle-' in the ID to get the localStorage key the toggle btn references
        elementId = elementId.replace("toggle-", "");
        var collapsibleDiv = $('#' + elementId);

        // Toggle the collapsed class
        collapsibleDiv.toggleClass('collapsed');

        // Update the state in localStorage
        var isCollapsed = collapsibleDiv.hasClass('in');
        localStorage.setItem(elementId, isCollapsed ? 'collapsed' : 'expanded');
        // Set Cookie value based on isCollapsed
        if (isCollapsed) {
            document.cookie = elementId + "=True; path=/";
        }
        else {
            console.log("isNotCollapsed");
            document.cookie = elementId + "=False; path=/";
        }
    }

    // Add event listener to each collapsible div
    $('.collapse-icon').on('click', function() {
        var elementId = this.id;
        toggleAndSaveState(elementId);
    });
});

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
        // WORKS
        var panelOrder = $("#draggable-homepage-panels").sortable("toArray");
        localStorage.setItem("homepage-panels-order", JSON.stringify(panelOrder));
    }

    // Function to load the saved order of panels from localStorage
    function loadSavedPanelOrder() {
        var savedOrder = localStorage.getItem("homepage-panels-order");
        console.log(savedOrder);

        if (savedOrder) {
            savedOrder = JSON.parse(savedOrder);
            console.log(savedOrder);
            // $("#draggable-homepage-panels").html("");
            
            for (var i = 0; i < savedOrder.length; i++) {
                $("#" + savedOrder[i]).appendTo("#draggable-homepage-panels");
            }
        }
    }
});
