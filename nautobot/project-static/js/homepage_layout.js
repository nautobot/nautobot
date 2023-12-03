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
