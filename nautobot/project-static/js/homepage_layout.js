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
document.addEventListener('DOMContentLoaded', function() {
    // Get the container element
    var draggableHomepagePanels = document.getElementById('draggable-homepage-panels');

    // Add event listeners for drag and drop events
    draggableHomepagePanels.addEventListener('dragstart', handleDragStart, false);
    draggableHomepagePanels.addEventListener('dragover', handleDragOver, false);
    draggableHomepagePanels.addEventListener('drop', handleDrop, false);

    // Load saved panel order on page load
    loadSavedPanelOrder();

    // Function to handle the start of a drag event
    function handleDragStart(e) {
        e.dataTransfer.setData('text/plain', e.target.id);
        e.target.classList.add('dragging');
    }

    // Function to handle a drag over event
    function handleDragOver(e) {
        e.preventDefault();
    }

    // Function to handle a drop event
    function handleDrop(e) {
        e.preventDefault();
        var draggedId = e.dataTransfer.getData('text/plain');
        var droppedOn = e.target.closest('.panel'); // Get the closest panel to the drop location

        if (droppedOn) { // Check if a panel was found
            var droppedOnId = droppedOn.id;
            swapElements(document.getElementById(draggedId), document.getElementById(droppedOnId));
            savePanelOrder();
        }
        
        // Remove the "dragging" class from the panel that was dragged
        document.getElementById(draggedId).classList.remove('dragging');
    }

    // Function to swap two elements
    function swapElements(obj1, obj2) {
        var temp = document.createElement("div");
        obj2.parentNode.insertBefore(temp, obj2);
        obj1.parentNode.insertBefore(obj2, obj1);
        temp.parentNode.insertBefore(obj1, temp);
        temp.parentNode.removeChild(temp);
    }

    // Function to save the order of panels in localStorage
    function savePanelOrder() {
        var panelOrder = Array.from(draggableHomepagePanels.children).map(function(panel) {
            return panel.id;
        });
        localStorage.setItem('homepage-panels-order', JSON.stringify(panelOrder));
    }

    // Function to load the saved order of panels from localStorage
    function loadSavedPanelOrder() {
        var savedOrder = localStorage.getItem('homepage-panels-order');

        if (savedOrder) {
            savedOrder = JSON.parse(savedOrder);

            // Append the panels in the saved order
            for (var i = 0; i < savedOrder.length; i++) {
                var panel = document.getElementById(savedOrder[i]);
                draggableHomepagePanels.appendChild(panel);
            }
        }

    }

    // Fade in the panels after they have been rearranged
    var opacity = 0; 
    var intervalID = 0; 
    window.onload = fadeIn; 
      
    function fadeIn() { 
        setInterval(show, 50); 
    } 
      
    function show() { 
        var body = document.getElementById("draggable-homepage-panels"); 
        opacity = Number(window.getComputedStyle(body) 
                        .getPropertyValue("opacity")); 
        if (opacity < 1) { 
            opacity = opacity + 0.1; 
            body.style.opacity = opacity 
        } else { 
            clearInterval(intervalID);
        } 
    } 
});
