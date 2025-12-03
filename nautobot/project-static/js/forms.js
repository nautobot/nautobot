/* ===========================
*  Utility Functions
*/

// Slugify
function slugify(s, num_chars) {
    s = s.replace(/[^_A-Za-z0-9\-\s\.]/g, '');  // Remove non-ascii chars
    s = s.replace(/^[\s\.]+|[\s\.]+$/g, '');    // Trim leading/trailing spaces
    s = s.replace(/[\-\.\s]+/g, '-');           // Convert spaces and decimals to hyphens
    s = s.toLowerCase();                        // Convert to lowercase
    s = s.replace(/-/g, '_');

    if (/^[^_A-Za-z]/.test(s)) {  // Slug must start with a letter or underscore only
        s = 'a' + s;
    }

    return s.substring(0, num_chars);           // Trim to first num_chars chars
}

/* ===========================
*  JS-ify Inputs
*/

function repopulateAutoField(context, targetField, sourceFields, maxLength, transformValue = null){
   const newValues = sourceFields.map(function(sourceFieldName){
        const sourceFieldId = `id_${sourceFieldName}`;
        return context.getElementById(sourceFieldId).value;
    })

    const newValue = newValues.join(" ")
    if(transformValue){
        targetField.value = transformValue(newValue, maxLength)
    } else {
        targetField.value = newValue.slice(0, maxLength)
    }
}

function repopulateIfChanged(targetField, repopulate){
    if(targetField.dataset.manuallyChanged === 'true'){
        return;
    }
    repopulate()
}

function watchManualChanges(field){
    field.dataset.manuallyChanged = Boolean(field.value)
    field.addEventListener('change', function(){
        field.dataset.manuallyChanged = Boolean(field.value)
    })
}

function watchSourceFields(context, targetField, sourceFields, repopulate){
    // Watch for any changes in source fields to regenerate the target field
    sourceFields.forEach(function(sourceFieldName){
        const sourceFieldId = `id_${sourceFieldName}`;
        const sourceField = context.getElementById(sourceFieldId);
        const onFieldUpdate = function(){ repopulateIfChanged(targetField, repopulate)}
        sourceField.addEventListener('keyup', onFieldUpdate)
        sourceField.addEventListener('change', onFieldUpdate)
    })
}

function watchRegenerateButton(context, targetField, repopulate){
    // If user clicks the "regenerate" button, set target field to be auto-populate again
    const regenerateButton = context.querySelector(`[data-regenerate=${targetField.getAttribute('id')}]`)
    regenerateButton.addEventListener('click', repopulate)
}

function getSlugField(){
    const slugField = document.getElementById("id_slug");
    if(slugField){
        return slugField
    }
    // If id_slug field is not to be found
    // check if it is renamed to key field like what we did for CustomField and Relationship
    return document.getElementById("id_key");
}

function initializeAutoField(context, field, sourceFieldsAttrName, defaultMaxLength = 255, transformValue = null){
    // Get source fields and length values set as html attributes on given field
    const sourceFields = field.getAttribute(sourceFieldsAttrName).split(" ");
    const length = field.getAttribute('maxlength') || defaultMaxLength

    // Prepare repopulate function with custom source fields and length set on this field
    const repopulateField = function() {
        repopulateAutoField(context, field, sourceFields, length, transformValue)
    }
    watchSourceFields(context, field, sourceFields, repopulateField);
    watchRegenerateButton(context, field, repopulateField);
    watchManualChanges(field);
}

function initializeSlugField(context){
    // Function to support slug fields auto-populate and slugify logic
    const vanilla_context = context[0] // jsify form passes jquery context
    const slugField = getSlugField()
    if(!slugField){
        return
    }
    initializeAutoField(vanilla_context, slugField, 'slug-source', 100, slugify);
}

function initializeAutoPopulateField(context){
    // Function to support other auto-populate fields like position for Device Module Bay
    const vanilla_context = context[0] // jsify form passes jquery context
    const fields = vanilla_context.querySelectorAll('[data-autopopulate]');

    fields.forEach(function(field){
        initializeAutoField(vanilla_context, field, 'source');
    })
}

function initializeFormActionClick(context){
    this_context = $(context);
    // Set formaction and submit using a link
    this_context.find('a.formaction').click(function(event) {
        event.preventDefault();
        var form = $(this).closest('form');
        form.attr('action', $(this).attr('href'));
        form.submit();
    });
}

// Bulk edit nullification
function initializeBulkEditNullification(context){
    this_context = $(context);
    this_context.find('input:checkbox[name=_nullify]').click(function() {
        var $field = $('#id_' + this.value);

        // If this is a NumberWithSelect (input-group + caret menu), don't hide the
        // field. Some other fields (e.g.Interface: LAG, Bridge) currently do nothing
        // when _nullify is checked, so this is consistent.
        var $group = $field.closest('.input-group');
        var isNumberWithSelect = $group.length &&
            $group.find('.input-group-btn .dropdown-menu a.set_value').length > 0;
        if (isNumberWithSelect) {
            return; // no UI change; _nullify still submitted
        }

        // Existing behavior for other fields
        $('#id_' + this.value).toggle('disabled');
    });
}

// Flatpickr selectors
function initializeDateTimePicker(context){
    flatpickr('.date-picker', {
        allowInput: true
    });
    flatpickr('.datetime-picker', {
        allowInput: true,
        enableSeconds: true,
        enableTime: true,
        time_24hr: true
    });
    flatpickr('.time-picker', {
        allowInput: true,
        enableSeconds: true,
        enableTime: true,
        noCalendar: true,
        time_24hr: true
    });
}

function initializeVLANModeSelection(context){
    this_context = $(context);
    if( this_context.find('select#id_mode').length > 0 ) { // Not certain for the length check here as if none is find it should not apply the onChange
        this_context.find('select#id_mode').on('change', function () {
            if ($(this).val() == '') {
                $('select#id_untagged_vlan').val('');
                $('select#id_untagged_vlan').trigger('change');
                $('select#id_tagged_vlans').val([]);
                $('select#id_tagged_vlans').trigger('change');
                $('select#id_untagged_vlan').parent().parent().hide();
                $('select#id_tagged_vlans').parent().parent().hide();
            }
            else if ($(this).val() == 'access') {
                $('select#id_tagged_vlans').val([]);
                $('select#id_tagged_vlans').trigger('change');
                $('select#id_untagged_vlan').parent().parent().show();
                $('select#id_tagged_vlans').parent().parent().hide();
            }
            else if ($(this).val() == 'tagged') {
                $('select#id_untagged_vlan').parent().parent().show();
                $('select#id_tagged_vlans').parent().parent().show();
            }
            else if ($(this).val() == 'tagged-all') {
                $('select#id_tagged_vlans').val([]);
                $('select#id_tagged_vlans').trigger('change');
                $('select#id_untagged_vlan').parent().parent().show();
                $('select#id_tagged_vlans').parent().parent().hide();
            }
        });
        this_context.find('select#id_mode').trigger('change');
    }
}

function initializeSortableList(context){
    this_context = $(context);
    // Rearrange options within a <select> list
    this_context.find('#move-option-up').bind('click', function() {
        var select_id = '#' + $(this).attr('data-target');
        $(select_id + ' option:selected').each(function () {
            var newPos = $(select_id + ' option').index(this) - 1;
            if (newPos > -1) {
                $(select_id + ' option').eq(newPos).before("<option value='" + $(this).val() + "' selected='selected'>" + $(this).text() + "</option>");
                $(this).remove();
            }
        });
    });
    this_context.find('#move-option-down').bind('click', function() {
        var select_id = '#' + $(this).attr('data-target');
        var countOptions = $(select_id + ' option').length;
        var countSelectedOptions = $(select_id + ' option:selected').length;
        $(select_id + ' option:selected').each(function () {
            var newPos = $(select_id + ' option').index(this) + countSelectedOptions;
            if (newPos < countOptions) {
                $(select_id + ' option').eq(newPos).after("<option value='" + $(this).val() + "' selected='selected'>" + $(this).text() + "</option>");
                $(this).remove();
            }
        });
    });
    this_context.find('#select-all-options').bind('click', function() {
        var select_id = '#' + $(this).attr('data-target');
        $(select_id + ' option').prop('selected',true);
    });
}

function initializeImagePreview(context){
    this_context = $(context);
    // Offset between the preview window and the window edges
    const IMAGE_PREVIEW_OFFSET_X = 20;
    const IMAGE_PREVIEW_OFFSET_Y = 10;
    // Preview an image attachment when the link is hovered over
    this_context.find('a.image-preview').on('mouseover', function(e) {
        // Twice the offset to account for all sides of the picture
        var maxWidth = window.innerWidth - (e.clientX + (IMAGE_PREVIEW_OFFSET_X * 2));
        var maxHeight = window.innerHeight - (e.clientY + (IMAGE_PREVIEW_OFFSET_Y * 2));
        var img = $('<img>').attr('id', 'image-preview-window').css({
            display: 'none',
            position: 'absolute',
            maxWidth: maxWidth + 'px',
            maxHeight: maxHeight + 'px',
            left: e.pageX + IMAGE_PREVIEW_OFFSET_X + 'px',
            top: e.pageY + IMAGE_PREVIEW_OFFSET_Y + 'px',
            boxShadow: '0 0px 12px 3px rgba(0, 0, 0, 0.4)',
        });

        // Remove any existing preview windows and add the current one
        $('#image-preview-window').remove();
        $('body').append(img);

        // Once loaded, show the preview if the image is indeed an image
        img.on('load', function(e) {
            if (e.target.complete && e.target.naturalWidth) {
                $('#image-preview-window').fadeIn('fast');
            }
        });

        // Begin loading
        img.attr('src', e.target.href);
    });

    // Fade the image out; it will be deleted when another one is previewed
    this_context.find('a.image-preview').on('mouseout', function() {
        $('#image-preview-window').fadeOut('fast');
    });
}

function initializeResultPerPageSelection(context){
    this_context = $(context);
    this_context.find('select#per_page').change(function() {
        this.form.submit();
    });
}

function initializeInputs(context) {
    const this_context = $(context);
    initializeSlugField(this_context)
    initializeAutoPopulateField(this_context)
    initializeFormActionClick(this_context)
    initializeBulkEditNullification(this_context)
    initializeDateTimePicker(this_context)
    initializeVLANModeSelection(this_context)
    initializeSortableList(this_context)
    initializeImagePreview(this_context)

    window.nb.checkbox.initializeCheckboxes()
    window.nb.select2.initializeSelect2Fields(this_context)
}

function jsify_form(context) {
    const this_context = $(context);
    // Pagination
    initializeInputs(this_context)
}

/* =======
*  Input Creators
*/

function submitOnEnter(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        if (!event.repeat) {
            event.target.form.requestSubmit();
        }

        event.preventDefault(); // Prevents the addition of a new line in the text field
    }
}

$(document).ready((e) => {
    jsify_form(this.document);
    initializeResultPerPageSelection(this.document);
    document.querySelectorAll("textarea.form-control").forEach(function(element) {element.addEventListener("keydown", submitOnEnter)});
})

