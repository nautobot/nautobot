// Capture the current theme from local storage and adjust the page to use the current theme.
const htmlEl = document.getElementsByTagName('html')[0];
const currentTheme = localStorage.getItem('theme') ? localStorage.getItem('theme') : null;

// CurrentTheme overrides auto-detection when specified by manually clicking theme button
if (currentTheme) {
    // Set theme setting to HTML dataset element, for CSS rendering
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
    
    // Toggle footer theme button to toggle
    if (theme == "dark") {
        displayLightBtn();
    }
    else {
        displayDarkBtn();
    }
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

function displayDarkBtn() {
    document.getElementById("btn-light-theme").style.display = 'none';
    document.getElementById("btn-dark-theme").style.display = '';
}
function displayLightBtn() {
    document.getElementById("btn-light-theme").style.display = '';
    document.getElementById("btn-dark-theme").style.display = 'none';
}

function setDarkTheme() {
    htmlEl.dataset.theme = "dark";
    displayLightBtn();
}

function setLightTheme() {
    htmlEl.dataset.theme = "light";
    displayDarkBtn();
}

// $('#theme_modal').on('show.bs.modal', function(event) {
//     var button = $(event.relatedTarget) // Button that triggered the modal
  
//     var modal = $(this)
  
//     modal.find('.modal-title').text('Select Nautobot Theme ')
//     modal.find('.modal-result').load('modals/modal_theme.html')
//   })

// $('#theme_modal').on('hidden.bs.modal', function() {
//     var modal = $(this)
//     modal.find('.modal-title').text('')
//     modal.find('.modal-result').text('')
// })

$('#theme_modal').on('show.bs.modal', function (event) {
    var button = $(event.relatedTarget);
    var obj = button.data('obj');
    var url = button.data('url');
    var modal_title = $(this).find('.modal-title');
    var modal_body = $(this).find('.modal-body');
    modal_title.text(obj);
    modal_body.empty();
    $.ajax({
        url: url,
        dataType: 'json',
        success: function(json) {
            $.each(json, function(i, segment) {
                modal_body.append(
                    'abcd' +
                    '<hr />'
                );
            })
        }
    });
});
