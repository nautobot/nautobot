// Toggle the display of device images within an SVG rack elevation
$('button.toggle-images').click(function() {
    var selected = $(this).attr('selected');
    var rack_elevation = $(".rack_elevation");
    if (selected) {
        $('.device-image', rack_elevation.contents()).addClass('hidden');
    } else {
        $('.device-image', rack_elevation.contents()).removeClass('hidden');
    }
    $(this).attr('selected', !selected);
    $(this).children('span').toggleClass('mdi-checkbox-marked-circle-outline mdi-checkbox-blank-circle-outline');
    return false;
});


// Key for localStorage to store preferred state for device name presentation
const window_ls_rack_device_fullname_display_key = 'rack_elevation_device_fullname';

// Default device name presentation: show untruncated name
let default_rackview_fullname_state = true;

// Pickup any local storage setting that may override default state above if set
if(window.localStorage.getItem(window_ls_rack_device_fullname_display_key) != null) {
    default_rackview_fullname_state = (window.localStorage.getItem(window_ls_rack_device_fullname_display_key) == 'true');
}

// Master function to update button, SVG links, and rack elevations to match provided state
function set_rack_device_fullname_state(display_fullname) {

    // First we update the button and stored state on button
    const toggle_button = document.querySelector('button.toggle-fullname')
    const toggle_button_icon_classList = toggle_button.querySelector('.mdi').classList;
    toggle_button.setAttribute('selected', display_fullname);
    toggle_button_icon_classList[(display_fullname && 'add') || 'remove']('mdi-checkbox-marked-circle-outline');
    toggle_button_icon_classList[(display_fullname && 'remove') || 'add']('mdi-checkbox-blank-circle-outline');

    // Next update the rack elevations to match desired state
    document.querySelectorAll(".rack_elevation").forEach((rack_elevation) => {
        set_rack_device_fullname_display(rack_elevation, display_fullname);
    })

    // Update the "Save SVG" links to match the presented state
    document.querySelectorAll('.rack_elevation_save_svg_link').forEach((link_el) => {
        const the_url = new URL(link_el.getAttribute('href'), window.location.href);
        the_url.searchParams.set('display_fullname', display_fullname);
        link_el.setAttribute('href', the_url);
    })

    // Save our current preference for state in localStorage for future use
    window.localStorage.setItem(window_ls_rack_device_fullname_display_key, display_fullname.toString());
}

// Given a object.rack_elevation (with nested SVG), update text fields display to given state
function set_rack_device_fullname_display(rack_elevation, display_fullname) {
    /**
     * set_device_text_display_state: A function generator function
     * Because we must pass a function to forEach to apply to each text element (JavaScript doesn't have sugar like jQuery does)
     * however we want to either conditionally add or remove the hidden class, we can on-the-fly change how this function will behave
     * forEach expects a function signature of function(element){}
     *
     * This function returns a function with that signature.
     *
     * This saves us from having to create two functions to either add or remove the hidden class.
     */
    function set_device_text_display_state(state) {
        return (text_element) => {
            const method = (state && 'remove') || 'add';
            text_element.classList[method]('hidden');
        }
    }

    rack_elevation.contentDocument.querySelectorAll('.rack-device-fullname').forEach(set_device_text_display_state(display_fullname));
    rack_elevation.contentDocument.querySelectorAll('.rack-device-shortname').forEach(set_device_text_display_state(!display_fullname));
}

// Fullname toggle button click event trigger
document.querySelector('button.toggle-fullname').addEventListener('click', (e) => {
    set_rack_device_fullname_state(!(e.target.getAttribute('selected') == 'true'));
    return false;
});

// Ensure fullname toggle button and links are in right state once painted to user
document.addEventListener('DOMContentLoaded', () => {
    set_rack_device_fullname_state(default_rackview_fullname_state);
});

// SVG objects get loaded after dom-ready so must be updated on load to match state
document.querySelectorAll('object.rack_elevation').forEach((obj) => {
    obj.addEventListener('load', (e) => {
        set_rack_device_fullname_display(e.target, default_rackview_fullname_state);
    })
})
