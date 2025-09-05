document.addEventListener('DOMContentLoaded', function() {
    const navbar = document.querySelector('.navbar-fixed-left');
    const navbarHeader = document.querySelector('.navbar-header');
    const mainContent = document.querySelector('#main-content');
    const footer = document.querySelector('#footer');
    const dropdownToggles = document.querySelectorAll('.navbar-fixed-left .navbar-nav > .dropdown > a[data-toggle="collapse"]');
    const dropdowns = document.querySelectorAll('.navbar-fixed-left .navbar-nav .collapse');
    const toggler = document.querySelector('.navbar-toggler');
    const togglerIcon = toggler.querySelector('.navbar-toggler-arrow');
    let lastDropdownId = sessionStorage.getItem('lastOpenedDropdown');
    let savedScrollPosition = sessionStorage.getItem('navbarScrollPosition');
    let activeLink = sessionStorage.getItem('activeLink');
    let expandedByHover = false;
    let manuallyToggled = sessionStorage.getItem('manuallyToggled') === 'true';

    // Function to reset stored dropdown state information
    function resetNavbarState() {
        sessionStorage.removeItem('lastOpenedDropdown');
        sessionStorage.removeItem('savedScrollPosition');
        sessionStorage.removeItem('activeLink');
        sessionStorage.removeItem('navbarCollapsed');
        expandedByHover = false;
    }

    toggler.addEventListener('click', function() {
        let isNowCollapsed;
        if (expandedByHover) {
            expandedByHover = false;
            isNowCollapsed = false;
        } else {
            isNowCollapsed = navbar.classList.toggle('collapsed');
        }
        sessionStorage.setItem('navbarCollapsed', isNowCollapsed ? 'true' : 'false');
        // Set 'navbarManuallyToggled' to track any manual toggle
        sessionStorage.setItem('navbarManuallyToggled', 'true');
        // Track if the action was an expansion or a collapse
        sessionStorage.setItem('navbarExpanded', !isNowCollapsed ? 'true' : 'false');
        if (isNowCollapsed) {
            togglerIcon.classList.add("mdi-rotate-90");
            togglerIcon.classList.remove("mdi-rotate-270");
        } else {
            togglerIcon.classList.remove("mdi-rotate-90");
            togglerIcon.classList.add("mdi-rotate-270");
        }
        adjustElementsForNavbarState(isNowCollapsed);
    });

    // Retrieve the navbar collapsed state from session storage on page load
    const navbarCollapsed = sessionStorage.getItem('navbarCollapsed') === 'true';
    if (navbarCollapsed) {
        navbar.classList.add('collapsed');
        togglerIcon.classList.remove("mdi-rotate-270");
        togglerIcon.classList.add("mdi-rotate-90");
        adjustElementsForNavbarState(true);
    }

    function adjustElementsForNavbarState(isCollapsed) {
        const marginLeftValue = isCollapsed ? '-240px' : '0px';
        mainContent.style.marginLeft = marginLeftValue;
        if(footer) footer.style.marginLeft = marginLeftValue;
        toggler.style.left = isCollapsed ? '-5px' : '225px';
    }

    // Expand navbar when hovering near the left edge of the screen
    document.addEventListener('mousemove', function(e) {
        if (
            e.clientX < 20  // 20px from the left edge
            && (e.clientY < 20 || e.clientY > 50) // not near the toggle button
            && navbar.classList.contains('collapsed')
        ) {
            navbar.classList.remove('collapsed');
            toggler.style.left = '225px';
            expandedByHover = true; // Set flag when expanded by hover
        } else if (expandedByHover && e.clientX > 240) {
            navbar.classList.add('collapsed');
            toggler.style.left = '-5px';
            expandedByHover = false; // Reset flag after auto-collapse
        }
    });

    function collapseNavbarIfNeeded() {
        const windowWidth = window.innerWidth;
        const navbarManuallyToggled = sessionStorage.getItem('navbarManuallyToggled') === 'true';
        const navbarExpanded = sessionStorage.getItem('navbarExpanded') === 'true';
        const isCollapsed = navbar.classList.contains('collapsed');

        if (windowWidth < 1007) {
            if (!isCollapsed) {
                navbar.classList.add('collapsed');
                togglerIcon.classList.remove("mdi-rotate-270");
                togglerIcon.classList.add("mdi-rotate-90");
                adjustElementsForNavbarState(true);
                sessionStorage.setItem('navbarCollapsed', 'true');
            }
        } else if (windowWidth >= 1007) {
            // Only expand automatically if it was not manually collapsed
            if (isCollapsed && (navbarManuallyToggled && navbarExpanded)) {
                navbar.classList.remove('collapsed');
                togglerIcon.classList.add("mdi-rotate-270");
                togglerIcon.classList.remove("mdi-rotate-90");
                adjustElementsForNavbarState(false);
                sessionStorage.setItem('navbarCollapsed', 'false');
            }
            // Do not automatically change the state if it was manually collapsed
        }
    }

    // Update the window resize listener
    function toggleNavbarOnResize() {
        collapseNavbarIfNeeded(); // Use the new function to decide whether to collapse
    }

    let debouncedToggleNavbarOnResize = debounce(toggleNavbarOnResize, 50);
    window.addEventListener('resize', debouncedToggleNavbarOnResize);

    // Select the navbar dropdown elements
    let navbarItems = document.querySelectorAll('.navbar-fixed-left .navbar-nav > .dropdown > .dropdown-toggle > #dropdown_title');

    // Add a title attribute and tooltip, only if necessary
    navbarItems.forEach(function(item) {
        // Check if the text overflows
        if (item.scrollWidth > item.clientWidth) {
            // Set the title attribute
            item.setAttribute('title', item.innerText);

            // Reinitialize Bootstrap tooltip
            $(item).tooltip();
        }
    });

    // Add an event listener for the home link click
    const homeLink = document.querySelector('.navbar-fixed-left .navbar-brand');
    if (homeLink) {
        homeLink.addEventListener('click', function() {
            resetNavbarState();
        });
    }

    // Close all dropdowns except the one specified
    function closeAllDropdownsExcept(exceptId) {
        dropdowns.forEach(function(collapse) {
            if (collapse.id !== exceptId && collapse.classList.contains('in')) {
                $(collapse).collapse('hide');
            }
        });
    }

    // Add click event listener to the dropdown links and save the clicked one
    function addLinkClickListeners() {
        const dropdownLinks = document.querySelectorAll('.navbar-fixed-left .navbar-nav > .dropdown > .nav-dropdown-menu > li > a');

        dropdownLinks.forEach(function(link) {
            link.addEventListener('click', function() {
                sessionStorage.setItem('activeLink', link.getAttribute('href'));
            });
        });
        collapseNavbarIfNeeded();
    }

    // Close all dropdowns except the last opened one
    dropdownToggles.forEach(function(toggle) {
        toggle.addEventListener('click', function(event) {
            event.preventDefault();
            const collapseElement = document.getElementById(this.getAttribute('href').substring(1));

            if (!collapseElement.classList.contains('in')) {
                closeAllDropdownsExcept(collapseElement.id);
                $(collapseElement).collapse('show');
                sessionStorage.setItem('lastOpenedDropdown', collapseElement.id);
            } else {
                $(collapseElement).collapse('hide');
                sessionStorage.removeItem('lastOpenedDropdown');
            }
        });
    });

    // Open the last opened dropdown
    if (lastDropdownId) {
        let lastDropdownMenu = document.getElementById(lastDropdownId);
        if (lastDropdownMenu && !lastDropdownMenu.classList.contains('in')) {
            $(lastDropdownMenu).collapse('show');
        }
    }

    // Restore the last saved scroll position
    if (savedScrollPosition) {
        navbar.scrollTop = savedScrollPosition;
    }

    // Function to adjust navbar header visibility based on scroll position and navbar collapsed state
    function adjustNavbarHeaderVisibility() {
        // Check if the navbar is collapsed and mainContent is defined
        if (navbar.classList.contains('collapsed') && mainContent) {
            const mainContentTop = mainContent.getBoundingClientRect().top;
            // Show or hide the navbar header based on mainContent's position
            if (mainContentTop < 0) {
                // Main content top is out of view, hide navbar header
                navbarHeader.style.top = '-60px'; // height of navbar header
            } else {
                // Main content top is in view, show navbar header
                navbarHeader.style.top = '0';
            }
        }
    }

    // Add scroll event listener to adjust navbar header visibility
    window.addEventListener('scroll', adjustNavbarHeaderVisibility);

    // Call the function initially to set the correct state when the page loads
    adjustNavbarHeaderVisibility();

    // Debounce function to limit the rate at which the handleScroll function is executed
    function debounce(func, wait, immediate) {
        let timeout;
        return function() {
            const context = this, args = arguments;
            const later = function() {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    }

    // Save the scroll position when the navbar is scrolled
    navbar.addEventListener('scroll', debounce(function() {
        sessionStorage.setItem('navbarScrollPosition', navbar.scrollTop);
    }, 250));

     // Add click event listeners to dropdown links
    addLinkClickListeners();

    // Apply the 'active' class to the previously clicked link
    if (activeLink) {
        let previouslyClickedLink = document.querySelector('.navbar-fixed-left .navbar-nav > .dropdown > .nav-dropdown-menu > li > a[href="' + activeLink + '"]');
        let currentLocation = window.location.pathname + window.location.search;
        let previouslyClickedLinkNoSearch = previouslyClickedLink.getAttribute('href').split('?')[0];

        if (previouslyClickedLink && (currentLocation.includes(previouslyClickedLink.getAttribute('href')) || currentLocation.includes(previouslyClickedLinkNoSearch))) {
            previouslyClickedLink.parentElement.classList.add('active');
        }
        else {
            sessionStorage.removeItem('activeLink');
        }
    }

});
