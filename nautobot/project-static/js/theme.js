const htmlEl = document.getElementsByTagName('html')[0];
const currentTheme = localStorage.getItem('theme') ? localStorage.getItem('theme') : null;
const tdLightTheme = document.getElementById('td-light-theme');
const tdDarkTheme = document.getElementById('td-dark-theme');
const tdSystemTheme = document.getElementById('td-system-theme');

// CSS file in base.html
var darkElement = document.getElementById("dark-theme");

// Only show page after it has fully loaded to prevent white screen flash
window.addEventListener('DOMContentLoaded', function () {
    // CurrentTheme overrides auto-detection when specified by manually clicking theme button
    if (currentTheme && currentTheme != "system") {
        // Set theme setting to HTML dataset element, for CSS rendering
        htmlEl.dataset.theme = currentTheme;

        // Set theme to light or dark if manually specified
        if (currentTheme == "light") {
            setLightThemeActive();
            setLightTheme();
        }
        else if (currentTheme == "dark") {
            setDarkThemeActive();
            setDarkTheme();
        }
    }
    else {
        setSystemThemeActive();
        // If user changes system theme, detect and change theme automatically
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
            // Detect and set theme based on what it was just changed to
            detectThemeSettings();
        })
        // Attempt to detect current system theme preferences and set theme to match
        detectThemeSettings();
    }
});

// When the user manually changes the theme, we need to save the new value on local storage
const toggleTheme = (theme) => {
    // Only set in local storage if user manually specifies a theme, enabling system/browser theme override
    htmlEl.dataset.theme = theme;
    localStorage.setItem('theme', theme);
    
    if (theme == "system") {
        setSystemThemeActive();
        // If user changes system theme, detect and change theme automatically
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
            // Detect and set theme based on what it was just changed to
            detectThemeSettings();
        })
        // Attempt to detect current system theme preferences and set theme to match
        detectThemeSettings()
    }
    else if (theme == "dark") {
        setDarkThemeActive();
        setDarkTheme();
    }
    else if (theme == "light") {
        setLightThemeActive();
        setLightTheme();
    }
    // Reload page after setting theme
    document.location.reload(true);
}

function detectThemeSettings() {
    // Attempt to detect current system theme preferences
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        // Dark mode
        setDarkTheme();
    }
    else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
        // Light mode
        setLightTheme();
    }
    else {
        // Default to light theme
        setLightTheme();
    }
}

function setDarkTheme() {
    // Set theme to dark
    htmlEl.dataset.theme = "dark";
    // Set theme cookie
    document.cookie = "theme=dark; path=/";
    // Enable dark element after page load
    // This is only needed for initial loading of page, before the cookie can be set and read (from above line)
    // For example, if set to System theme, but your system is set to dark mode
    //  Nautobot initially loads in as light theme, then any page refresh or new page will load in dark theme
    // This line prevents that initial light screen load, with an initial, one-time "flash" from light to dark
    darkElement.disabled = undefined;
}

function setLightTheme() {
    htmlEl.dataset.theme = "light";
    document.cookie = "theme=light; path=/";
    darkElement.disabled = "disabled";
}

/* Highlights the active selection in the theme-selection modal */
function setLightThemeActive() {
    tdSystemTheme.classList.remove("active-theme");
    tdDarkTheme.classList.remove("active-theme");
    tdLightTheme.classList.add("active-theme");
}

function setDarkThemeActive() {
    tdSystemTheme.classList.remove("active-theme");
    tdDarkTheme.classList.add("active-theme");
    tdLightTheme.classList.remove("active-theme");
}

function setSystemThemeActive() {
    tdSystemTheme.classList.add("active-theme");
    tdDarkTheme.classList.remove("active-theme");
    tdLightTheme.classList.remove("active-theme");
}