$(document).ready(function() {
    // Function to toggle and save state for a specific collapsible element
    function toggleAndSaveState(elementId) {
        // Remove 'toggle-' in the ID to get the localStorage key the toggle btn references
        elementId = elementId.replace("toggle-", "");
        var collapsibleDiv = $('#' + elementId);

        // Toggle the collapsed class
        collapsibleDiv.toggleClass('collapsed');

        // Update the state in localStorage
        var isCollapsed = collapsibleDiv.hasClass('collapsed');
        localStorage.setItem(elementId, isCollapsed ? 'collapsed' : 'expanded');
    }

    // Function to set initial state for all collapsible elements
    function setInitialStates() {
        $('.collapsible-div').each(function() {
            var elementId = this.id;
            var isCollapsed = localStorage.getItem(elementId) === 'collapsed';

            // Set initial state based on localStorage
            if (isCollapsed) {
                $(this).removeClass('in');
            }
        });
    }

    // Set initial states on page load
    setInitialStates();

    // Add event listener to each collapsible div
    $('.collapse-icon').on('click', function() {
        var elementId = this.id;
        toggleAndSaveState(elementId);
    });
});
