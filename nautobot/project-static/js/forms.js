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

// Static choice selection
function initializeCheckboxes(context){
    // "Toggle" checkbox for object lists (PK column)
    document.querySelectorAll('input[type="checkbox"].toggle').forEach(toggleCheckbox => {
        toggleCheckbox.addEventListener('click', function () {
            const isChecked = this.checked;
            // Check/uncheck all pk column checkboxes in the table
            this.closest('table')
                .querySelectorAll('input[type="checkbox"][name="pk"]:not([visually-hidden])')
                .forEach(checkbox => checkbox.checked = isChecked);

            // Show the "select all" box if present
            const selectAllBox = document.getElementById('select_all_box');
            if (selectAllBox) {
                if (isChecked) {
                    // unhide the select all objects form that contains the bulk action buttons
                    selectAllBox.classList.remove('visually-hidden');
                } else {
                    const selectAll = document.getElementById('select_all');
                    if (selectAll) selectAll.checked = false;
                }
            }
        });
    });

    // Uncheck the "toggle" and "select all" checkboxes if an item is unchecked
    document.querySelectorAll('input[type="checkbox"][name="pk"]').forEach(itemCheckbox => {
        itemCheckbox.addEventListener('click', function () {
            if (!this.checked) {
                document.querySelectorAll('input[type="checkbox"].toggle, #select_all')
                    .forEach(checkbox => checkbox.checked = false);
            }
        });
    });
}

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

function initializeDynamicFilterForm(context){
    this_context = $(context);

    function initializeDynamicFilterSelect(element) {
        // On change of a select field in default filter form
        // Replicate that change into dynamic filter form and vice-versa
        $(element).on("change", function (e){
            let field_name = $(this).attr("name");
            let field_values = $(this).select2('data');
            let form_id = $(this).parents("form").attr("id");

            let default_filters_field_dom = $(`#default-filter form select[name=${field_name}]`);
            let advanced_filters_field_dom = $(`#advanced-filter #filterform-table tbody tr td select[name=${field_name}]`);

            // Only apply logic if fields with same name attr are on both advanced and default filter form
            if(default_filters_field_dom.length && advanced_filters_field_dom.length){
                let default_filters_field_ids = default_filters_field_dom.select2('data').map(data => data["id"]);
                let advanced_filters_field_ids = advanced_filters_field_dom.select2('data').map(data => data["id"]);

                // Only change field value if both fields do not have equal values
                if (JSON.stringify(advanced_filters_field_ids) !== JSON.stringify(default_filters_field_ids)){
                    if(form_id === "dynamic-filter-form"){
                        changeSelect2FieldValue(default_filters_field_dom, field_values);
                    }
                    else {
                        changeSelect2FieldValue(advanced_filters_field_dom, field_values);
                    }
                }
            }
        });
    }

    function initializeDynamicFilterInput(element) {
        // On change of input field in default filter form
        // Replicate that change into dynamic filter form and vice-versa
        $(element).on("change", function (e){
            let field_name = $(this).attr("name");
            let field_value = $(this).val();
            let form_id = $(this).parents("form").attr("id");
            let default_filters_field_dom = $(`#default-filter form input[name=${field_name}]`);
            let advanced_filters_field_dom = $(`#advanced-filter #filterform-table tbody tr td input[name=${field_name}]`);

            // Only apply logic if fields with same name attr are on both advanced and default filter form
            if(default_filters_field_dom.length && advanced_filters_field_dom.length){
                // Only change field value if both fields do not have equal values
                if (default_filters_field_dom.val() !== advanced_filters_field_dom.val()){
                    if(form_id === "dynamic-filter-form"){
                        default_filters_field_dom.val(field_value);
                    }
                    else {
                        advanced_filters_field_dom.val(field_value);
                    }
                }
            }
        })
    }

    // Dynamic filter form
    this_context.find(".lookup_type-select").bind("change", function(){
        let parent_element = $(this).parents("tr")
        let lookup_type = parent_element.find(".lookup_type-select")
        let lookup_type_val = lookup_type.val()
        let contenttype = lookup_type.attr("data-contenttype")
        let lookup_value_element = parent_element.find(".lookup_value-input")

        if(lookup_type_val){
            $.ajax({
                url: `/api/ui/core/filterset-fields/lookup-value-dom-element/?field_name=${lookup_type_val}&content_type=${contenttype}`,
                async: true,
                headers: {'Accept': '*/*'},
                type: 'GET',
            }).done(function (response) {
                newEl = $(response)
                newEl.addClass("lookup_value-input")
                replaceEl(lookup_value_element, newEl)
                if (newEl.prop("tagName") == "SELECT") {
                    initializeDynamicFilterSelect(newEl);
                } else {
                    initializeDynamicFilterInput(newEl);
                }
            }).fail(function (xhr, status, error) {
                // Default to Input:text field if error occurs
                createInput(lookup_value_element)
            });
        }

    })

    // On change of lookup_field or lookup_type field in filter form reset field value
    this_context.find(".lookup_field-select, .lookup_type-select").on("change", function(){
        let parent_element = $(this).parents("tr")
        let lookup_field_element = parent_element.find(".lookup_field-select")
        let lookup_type_element = parent_element.find(".lookup_type-select")
        let lookup_value_element = parent_element.find(".lookup_value-input")

        if ($(this)[0] == lookup_field_element[0]) {
            lookup_type_element.val(null).trigger('change');
        }
        lookup_value_element.val(null).trigger('change')

    })

    // By default on lookup_value field names are form-\d-lookup_value, thats why
    // on page load we change all `lookup_value` name to its relevant `lookup_type` value
    this_context.find(".dynamic-filterform").each(function(){
        lookup_type_value = $(this).find(".lookup_type-select").val();
        lookup_value = $(this).find(".lookup_value-input");
        lookup_value.attr("name", lookup_type_value);
    })

    // Remove applied filters
    this_context.find(".remove-filter-param").on("click", function(){
        let query_params = new URLSearchParams(location.search);
        if (query_params.has("saved_view")) {
            // Need to reverse-engineer the "real" query params from the rendered page
            for (let element of document.getElementsByClassName("filter-selection-choice-remove")) {
                let key = element.getAttribute("data-field-parent");
                let value = element.getAttribute("data-field-value");
                if (!query_params.has(key, value)) {
                    query_params.append(key, value);
                }
            }
        }
        let type = $(this).attr("data-field-type");
        let field_value = $(this).attr("data-field-value");

        if (type === "parent") {
            // Remove all instances of this query param
            query_params.delete(field_value);

        } else {
            // Remove this specific instance of this query param
            let parent = $(this).attr("data-field-parent");
            query_params.delete(parent, field_value);
        }
        if (query_params.has("saved_view")) {
            var all_filters_removed = true

            const non_filter_params = ["saved_view", "sort", "per_page", "table_changes_pending", "all_filters_removed", "clear_view"]

            query_params.forEach((value, key) => {
                if (!non_filter_params.includes(key)){
                    all_filters_removed = false
                }
            })

            if (all_filters_removed && !query_params.has("all_filters_removed")){
                query_params.append("all_filters_removed", true);
            }
        }
        location.assign("?" + query_params);
    })

    // On submit of filter form
    this_context.find("#dynamic-filter-form, #default-filter form").on("submit", function(e){
        e.preventDefault()
        let dynamic_form = $("#dynamic-filter-form");
        dynamic_form.find(`input[name*="form-"], select[name*="form-"]`).removeAttr("name")

        // Append q form field to dynamic filter form via hidden input
        let q_field = $('#id_q')
        let q_field_phantom = $('<input type="hidden" name="q" />')
        q_field_phantom.val(q_field.val())
        dynamic_form.append(q_field_phantom);

        // Get the serialized data from the forms and:
        // 1) filter out query_params which values are empty e.g ?sam=&dan=2 becomes dan=2
        // 2) combine the two forms into a single set of data without duplicate entries
        let search_query = new URLSearchParams();
        let dynamic_query = new URLSearchParams(new FormData(document.getElementById("dynamic-filter-form")));
        const urlParams = new URLSearchParams(window.location.search);
        const non_filter_params = ["saved_view", "sort", "per_page", "table_changes_pending", "clear_view"]
        urlParams.forEach((value, key) => {
            if (non_filter_params.includes(key)){
                search_query.append(key, value)
            }
        })
        dynamic_query.forEach((value, key) => { if (value != "") { search_query.append(key, value); }});
        // Some list views may lack a default-filter form
        let default_query = new URLSearchParams(new FormData(document.getElementById("default-filter")?.firstElementChild));
        default_query.forEach((value, key) => {
            if (value != "" && !search_query.has(key, value)) { search_query.append(key, value); }
        });
        $("#FilterForm_modal").modal("hide");

        if (search_query.has("saved_view")) {
            var all_filters_removed = true

            const non_filter_params = ["saved_view", "sort", "per_page", "table_changes_pending", "all_filters_removed", "clear_view"]

            search_query.forEach((value, key) => {
                if (!non_filter_params.includes(key)){
                    all_filters_removed = false
                }
            })

            if (all_filters_removed && !search_query.has("all_filters_removed")){
                search_query.append("all_filters_removed", true);
            }
        }
        location.assign("?" + search_query);
    })

    // On submit of filter search form
    this_context.find("#search-form").on("submit", function(e){
        // Since the Dynamic Filter Form will already grab my q field, just have it do a majority of the work.
        e.preventDefault()
        $("#dynamic-filter-form").submit()
    })

    // On clear of filter form
    this_context.find("#dynamic-filter-form, #default-filter form").on("reset", function(e){
        e.preventDefault()
        // make two copies of url params
        const urlParams = new URLSearchParams(window.location.search);
        const newUrlParams = new URLSearchParams(window.location.search);
        // every query string that is non-filter-related
        const non_filter_params = ["saved_view", "sort", "per_page", "table_changes_pending", "all_filters_removed", "clear_view"]
        for (const [key, value] of urlParams.entries()) {
            // remove filter params
            if (non_filter_params.includes(key) === false) {
                newUrlParams.delete(key, value)
            }
        }
        if (!newUrlParams.has("all_filters_removed")){
            newUrlParams.append("all_filters_removed", true)
        }
        location.assign("?" + newUrlParams.toString())
    })


    // Clear new row values upon creation
    this_context.find(".dynamic-filterform-add .add-row").click(function(){
        let new_fields_parent_element = $(".dynamic-filterform").last()
        let lookup_field_classes = [".lookup_field-select", ".lookup_type-select", ".lookup_value-input"];
        lookup_field_classes.forEach(field_class => {
            let element = new_fields_parent_element.find(field_class);
            element.val(null).trigger('change')
        })
        // reinitialize jsify_form
        initializeDynamicFilterForm($(document));
    })

    function changeSelect2FieldValue(dom_element, values){
        dom_element.val(null)
        values.forEach(function (value){
            // Does an element already exist?
            if (!dom_element.find("option[value='" + value.id + "']").length) {
                let new_option = new Option(value.text, value.id, true, true);
                dom_element.append(new_option);
            }
        })
        dom_element.val(values.map(data => data["id"]));
        dom_element.trigger('change');
    }

    this_context.find("#default-filter form select, #advanced-filter select").each(function() {
        initializeDynamicFilterSelect(this);
    });

    // On change of input field in default filter form
    // Replicate that change into dynamic filter form and vice-versa
    this_context.find("#default-filter form input, #advanced-filter input").each(function() {
        initializeDynamicFilterInput(this);
    });
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

function initializeSelectAllForm(context){
    // selectAll is the checkbox that selects all objects
    const selectAll = document.querySelector('#select_all');
    // selectAllBox is the div that contains the form bulk action buttons
    const selectAllBox = document.querySelector('#select_all_box');

    if (selectAll && selectAllBox) {
        selectAll.addEventListener('click', function () {
            // If the selectAll checkbox is checked, enable all form bulk action buttons
            const isChecked = this.checked;
            selectAllBox.querySelectorAll('button').forEach(button => {
                button.disabled = !isChecked;
            });
        });
    }
}

function initializeResultPerPageSelection(context){
    this_context = $(context);
    this_context.find('select#per_page').change(function() {
        this.form.submit();
    });
}

function replaceEl(replaced_el, replacing_el) {
    parent = replaced_el.parent()
    parent.html(replacing_el)
    initializeInputs(parent)
}

function initializeInputs(context) {
    const this_context = $(context);
    initializeCheckboxes(this_context)
    initializeSlugField(this_context)
    initializeAutoPopulateField(this_context)
    initializeFormActionClick(this_context)
    initializeBulkEditNullification(this_context)
    initializeDateTimePicker(this_context)
    initializeVLANModeSelection(this_context)
    initializeSortableList(this_context)
    initializeImagePreview(this_context)
    initializeDynamicFilterForm(this_context)
    initializeSelectAllForm(this_context)

    initializeSelect2Fields(this_context)
}

function jsify_form(context) {
    const this_context = $(context);
    // Pagination
    initializeInputs(this_context)
}

/* =======
*  Input Creators
*/


function createInput(element){
    input_field = `
    <input
    type="text"
    name="${element.attr('name')}"
    class="lookup_value-input form-control"
    id="${element.attr('id')}"
    />`
    replaceEl(element, input_field)
}

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

