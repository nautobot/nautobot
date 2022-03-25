// Capture the current theme from local storage and adjust the page to use the current theme.
const htmlEl = document.getElementsByTagName('html')[0];
const currentTheme = localStorage.getItem('theme') ? localStorage.getItem('theme') : null;

if (currentTheme) {
    htmlEl.dataset.theme = currentTheme;
    
    // Toggle footer theme button to toggle
    if (currentTheme == "dark") {
        displayLightBtn();
    }
    else {
        displayDarkBtn();
    }
}
else {
    // Default to light theme
    displayDarkBtn();
}
// When the user changes the theme, we need to save the new value on local storage
const toggleTheme = (theme) => {
    htmlEl.dataset.theme = theme;
    localStorage.setItem('theme', theme);
    
    // Toggle footer theme button to toggle
    if (theme == "dark") {
        displayLightBtn();
    }
    else {
        displayDarkBtn();
    }
}

function displayDarkBtn() {
    document.getElementById("btn-light-theme").style.display = 'none';
    document.getElementById("btn-dark-theme").style.display = '';
}
function displayLightBtn() {
    document.getElementById("btn-light-theme").style.display = '';
    document.getElementById("btn-dark-theme").style.display = 'none';
}
