const htmlEl = document.getElementsByTagName('html')[0];
const currentTheme = localStorage.getItem('theme') ? localStorage.getItem('theme') : null;

var darkElement = document.getElementById("dark-theme");

// CurrentTheme overrides auto-detection when specified by manually clicking theme button
if (currentTheme && currentTheme != "system") {
    // Set theme setting to HTML dataset element, for CSS rendering
    htmlEl.dataset.theme = currentTheme;

    // Set theme to light or dark if manually specified
    if (currentTheme == "light") {
        setLightTheme();
    }
    else if (currentTheme == "dark") {
        setDarkTheme();
    }
}
else {
    // If user changes system theme, detect and change theme automatically
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
        // Detect and set theme based on what it was just changed to
        detectThemeSettings()
    })
    // Attempt to detect current system theme preferences and set theme to match
    detectThemeSettings()
}

// When the user manually changes the theme, we need to save the new value on local storage
const toggleTheme = (theme) => {
    // Only set in local storage if user manually specifies a theme, enabling system/browser theme override
    htmlEl.dataset.theme = theme;
    localStorage.setItem('theme', theme);
    
    if (theme == "system") {
        // If user changes system theme, detect and change theme automatically
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
            // Detect and set theme based on what it was just changed to
            detectThemeSettings()
        })
        // Attempt to detect current system theme preferences and set theme to match
        detectThemeSettings()
    }
    else if (theme == "dark") {
        setDarkTheme();
    }
    else if (theme == "light") {
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
    htmlEl.dataset.theme = "dark";
    darkElement.disabled = undefined;
}

function setLightTheme() {
    htmlEl.dataset.theme = "light";
    darkElement.disabled = "disabled";
}