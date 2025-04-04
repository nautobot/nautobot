// Enables panels on homepage to be collapsed and expanded
document.addEventListener("DOMContentLoaded", function() {
    // Function to toggle and save state for a specific collapsible element
    function toggleAndSaveState(elementId) {
        // Remove "toggle-" in the ID to get the localStorage key the toggle btn references
        elementId = elementId.replace("toggle-", "");
        var collapsibleDiv = document.getElementById(elementId);

        // Toggle the collapsed class
        var isCollapsed = collapsibleDiv.classList.toggle("collapsed")

        // Rotate glyphicon
        collapsibleDiv.classList.toggle("rotated180");

        // Update the state in localStorage
        var isCollapsed = collapsibleDiv.classList.contains("in");
        localStorage.setItem(elementId, isCollapsed ? "collapsed" : "expanded");
        // Set Cookie value based on isCollapsed
        if (isCollapsed) {
            document.cookie = elementId + "=True; path=/";
        } else {
            document.cookie = elementId + "=False; path=/";
        }
    }

    // Add event listener to each collapsible div
    var collapseIcons = document.querySelectorAll(".collapse-icon");
    collapseIcons.forEach(function(icon) {
        icon.addEventListener("click", function() {
            var elementId = this.id;
            toggleAndSaveState(elementId);
        });
    });
});

// Enables panels on homepage to be rearranged via drag and drop
document.addEventListener("DOMContentLoaded", function() {
    // Get the container element
    var draggableHomepagePanels = document.getElementById("draggable-homepage-panels");

    // Add event listeners for drag and drop events
    draggableHomepagePanels.addEventListener("dragstart", handleDragStart, false);
    draggableHomepagePanels.addEventListener("dragend", handleDragEnd, false);
    draggableHomepagePanels.addEventListener("dragover", handleDragOver, false);
    draggableHomepagePanels.addEventListener("drop", handleDrop, false);

    // Enable panel dragging
    enablePanelDragging();

    // Load saved panel order on page load
    loadSavedPanelOrder();

    // Function to handle the start of a drag event
    function handleDragStart(e) {

        // Get the element the user clicked on
        const clickedElement = document.elementFromPoint(e.clientX, e.clientY);

        // Only allow drag if the handle is in the panel-heading
        if (!clickedElement || !clickedElement.closest(".panel-heading")) {
            e.preventDefault();
            return;
        }
            e.dataTransfer.clearData("text/plain");
            e.dataTransfer.setData("text/plain", e.target.id);
            e.target.classList.add("dragging");
    }

    function handleDragEnd(e) {
        e.target.classList.remove("dragging");
    }

    // Function to handle a drag over event
    function handleDragOver(e) {
        e.preventDefault();
    }

    // Function to handle a drop event
    function handleDrop(e) {
        e.preventDefault();

        let dragged = document.getElementById(e.dataTransfer.getData("text/plain"));
        let insertBefore = null;

        /* Were we dropped onto another panel? */
        let droppedOn = e.target.closest(".panel");
        if (droppedOn) {
            /* Were we dropped in the top half or the bottom half of the target panel? */
            boundingClientRect = droppedOn.getBoundingClientRect();
            if (e.clientY < boundingClientRect.top + (boundingClientRect.height / 2)) {
                /* Top half - insert before that panel */
                insertBefore = droppedOn;
            } else {
                /* Bottom half - insert after that panel */
                insertBefore = droppedOn.nextSibling;
            }
        } else {
            /* We were dropped into empty space - find the closest panel by geometry */
            for (let child of this.children) {
                /* Are we in the correct column? */
                if (child.offsetLeft > e.offsetX) {
                    /* Found the first child that is too far to the right, so we insert before that child */
                    insertBefore = child;
                    break;
                } else if (child.offsetLeft + child.offsetWidth >= e.offsetX) {
                    /* Child is in the correct column */
                    if (child.offsetTop >= e.offsetY) {
                        /* Found the first child in this column we were dropped above, so we insert before that child */
                        insertBefore = child;
                        break;
                    }
                }
            }
        }

        if (insertBefore) {
            this.insertBefore(dragged, insertBefore);
        } else {
            /* Add to end of the list */
            this.append(dragged);
        }

        savePanelOrder();

        // Remove the "dragging" class from the panel that was dragged
        dragged.classList.remove("dragging");
    }

    // Function to save the order of panels in localStorage
    function savePanelOrder() {
        var panelOrder = Array.from(draggableHomepagePanels.children).map(function(panel) {
            return panel.id;
        });
        localStorage.setItem("homepage-panels-order", JSON.stringify(panelOrder));
    }

    // Function to load the saved order of panels from localStorage
    function loadSavedPanelOrder() {
        var savedOrder = localStorage.getItem("homepage-panels-order");

        if (savedOrder) {
            savedOrder = JSON.parse(savedOrder);

            // Append the panels in the saved order
            for (var i = 0; i < savedOrder.length; i++) {
                var panel = document.getElementById(savedOrder[i]);
                if (panel) {
                    draggableHomepagePanels.appendChild(panel);
                }
            }
        }
    }

    // Enable panel dragging
    function enablePanelDragging() {
        for (let panel of draggableHomepagePanels.children) {
            panel.draggable = true;
        }

    }

    // Fade in the panels after they have been rearranged
    var opacity = 0; 
    var intervalID = 0; 
    window.onload = fadeIn; 
      
    function fadeIn() { 
        intervalID = setInterval(show, 50); 
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
