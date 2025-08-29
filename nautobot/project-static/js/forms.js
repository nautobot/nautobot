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

// Parse URLs which may contain variable references to other field values
function parseURL(url) {
    var filter_regex = /\{\{([a-z_]+)\}\}/g;
    var match;
    var rendered_url = url;
    var filter_field;
    while (match = filter_regex.exec(url)) {
        filter_field = $('#id_' + match[1]);
        var custom_attr = $('option:selected', filter_field).attr('api-value');
        if (custom_attr) {
            rendered_url = rendered_url.replace(match[0], custom_attr);
        } else if (filter_field.val()) {
            rendered_url = rendered_url.replace(match[0], filter_field.val());
        } else if (filter_field.attr('data-null-option')) {
            rendered_url = rendered_url.replace(match[0], 'null');
        }
    }
    return rendered_url
}

// Assign color picker selection classes
function colorPickerClassCopy(data, container) {
    if (data.element) {
        // Swap the style
        $(container).attr('style', $(data.element).attr("style"));
    }
    return data.text;
}


/* ===========================
*  JS-ify Inputs
*/

// Static choice selection
function initializeStaticChoiceSelection(context, dropdownParent=null){
    this_context = $(context);
    this_context.find('.nautobot-select2-static').select2({
        allowClear: true,
        placeholder: "---------",
        theme: "bootstrap",
        width: "off",
        dropdownParent: dropdownParent
    });
}

// Static choice selection
function initializeCheckboxes(context){
    this_context = $(context);

    // Track last selected checkbox for range selection
    let lastSelectedIndex = null;

    // "Toggle" checkbox for object lists (PK column)
    this_context.find('input:checkbox.toggle').click(function() {
        $(this).closest('table').find('input:checkbox[name=pk]:visible').prop('checked', $(this).prop('checked'));

        // Show the "select all" box if present
        if ($(this).is(':checked')) {
            $('#select_all_box').removeClass('hidden');
        } else {
            $('#select_all').prop('checked', false);
            $('#select_all_box').addClass('hidden');
        }

        // Reset last selected index when using toggle all
        lastSelectedIndex = null;
    });

    // Enhanced checkbox click handler with shift-click range selection
    this_context.find('input:checkbox[name=pk]').click(function (event) {
        const $table = $(this).closest('table');
        const $allCheckboxes = $table.find('input:checkbox[name=pk]:visible');
        const currentIndex = $allCheckboxes.index(this);

        // Handle shift-click for range selection/deselection
        if (event.shiftKey && lastSelectedIndex !== null) {
            // Create range from previous click to current click
            const startIndex = Math.min(lastSelectedIndex, currentIndex);
            const endIndex = Math.max(lastSelectedIndex, currentIndex);

            // Use the clicked item's new state for entire range
            const shouldSelect = this.checked;

            // Apply to entire range
            for (let i = startIndex; i <= endIndex; i++) {
                $allCheckboxes.eq(i).prop('checked', shouldSelect);
            }
        }

        // Always update anchor to current click (normal click or shift+click)
        lastSelectedIndex = currentIndex;

        // Uncheck the "toggle" and "select all" checkboxes if any item is unchecked
        const hasUnchecked = $allCheckboxes.filter(':not(:checked)').length > 0;
        if (hasUnchecked) {
            $('input:checkbox.toggle, #select_all').prop('checked', false);
            $('#select_all_box').addClass('hidden');
        }
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

// Color Picker
function initializeColorPicker(context, dropdownParent=null){
    this_context = $(context);
    this_context.find('.nautobot-select2-color-picker').select2({
        allowClear: true,
        placeholder: "---------",
        theme: "bootstrap",
        templateResult: colorPickerClassCopy,
        templateSelection: colorPickerClassCopy,
        width: "off",
        dropdownParent: dropdownParent
    });
}

/**
 * Retrieves the value of a property from a nested object using a string path.
 *
 * This method supports accessing deeply nested properties within an object.
 * It is created to support extraction of nested values in the display-field
 * and value-field for DynamicChoiceField.
 *
 * @param {Object} response - The object from which to retrieve the value.
 * @param {string} fieldPath - The string representing the path to the desired property.
 * @returns {*} The value of the specified property, or null if the path is invalid or the object is not found.
 *
 * @example
 * let response = {
 *   "id": 1234,
 *   "vlan": {
 *     "name": "myvlan"
 *   },
 *   "interfaces": [
 *     { "name": "eth0", "status": "up" },
 *     { "name": "eth1", "status": "down" }
 *   ]
 * }
 * // returns "myvlan"
 * resolvePath(response, "vlan.name")
 *
 * // returns "eth0"
 * resolvePath(response, "interfaces[0].name")
 *
 * // returns "eth0"
 * resolvePath(response, "interfaces.0.name")
 */
function resolvePath(response, fieldPath) {
    if (!fieldPath)
        return null;

    if (typeof response !== 'object' || response === null || !response) {
        console.error('Invalid response object');
        return null;
    }

    return fieldPath
           .replace(/\[|\]\.?/g, '.')
           .split('.')
           .filter(value => value)
           .reduce((memo, value) => memo && memo[value], response);
}

// Dynamic Choice Selection
function initializeDynamicChoiceSelection(context, dropdownParent=null){
    this_context = $(context);
    this_context.find('.nautobot-select2-api').each(function(){
        thisobj = $(this);
        placeholder = "---------";
        thisobj.select2({
            allowClear: true,
            placeholder: placeholder,
            theme: "bootstrap",
            width: "off",
            dropdownParent: dropdownParent,
            ajax: {
                delay: 500,

                url: function(params) {
                    var element = this[0];
                    var url = parseURL(element.getAttribute("data-url"));

                    if (url.includes("{{")) {
                        // URL is not fully rendered yet, abort the request
                        return false;
                    }
                    return url;
                },

                data: function(params) {
                    var element = this[0];
                    // Paging. Note that `params.page` indexes at 1
                    var offset = (params.page - 1) * 50 || 0;
                    // Base query params
                    var parameters = {
                        q: params.term,
                        limit: 50,
                        offset: offset,
                    };

                    // Set api_version
                    api_version = $(element).attr("data-api-version");
                    if(api_version){
                        parameters["api_version"] = api_version;
                    }


                    // Allow for controlling the depth setting from within APISelect
                    parameters.depth = parseInt($(element).attr('data-depth'))

                    // Attach any extra query parameters
                    $.each(element.attributes, function(index, attr){
                        if (attr.name.includes("data-query-param-")){
                            var param_name = attr.name.split("data-query-param-")[1];

                            $.each($.parseJSON(attr.value), function(index, value) {
                                // Referencing the value of another form field
                                if (value.startsWith('$')) {
                                    let element_id = $(element).attr("id");
                                    let ref_field;

                                    if(element_id.includes("id_form-")){
                                        let id_prefix = element_id.match(/id_form-[0-9]+-/i, "")[0];
                                        ref_field = $("#" + id_prefix + value.slice(1));
                                    }
                                    // If the element is in a table row with a class containing "dynamic-formset"
                                    // We need to find the reference field in the same row
                                    else if ($(element).closest("tr") && $(element).closest("tr").attr("class") && $(element).closest("tr").attr("class").includes("dynamic-formset")){
                                        ref_field = $(element).closest("tr").find("select[id*=" + value.slice(1) + "]");
                                    }
                                    else {
                                        ref_field = $('#id_' + value.slice(1));
                                    }

                                    if (ref_field.val() && ref_field.is(":visible")) {
                                        value = ref_field.val();
                                    } else if (ref_field.attr("required") && ref_field.attr("data-null-option")) {
                                        value = "null";
                                    } else {
                                        return true;  // Skip if ref_field has no value
                                    }
                                }
                                if (param_name in parameters) {
                                    if (Array.isArray(parameters[param_name])) {
                                        parameters[param_name].push(value);
                                    } else {
                                        parameters[param_name] = [parameters[param_name], value];
                                    }
                                } else {
                                    parameters[param_name] = value;
                                }
                            });
                        }
                    });

                    // Attach contenttype to parameters
                    contenttype = $(element).attr("data-contenttype");
                    if(contenttype){
                        parameters["content_type"] = contenttype;
                    }

                    // This will handle params with multiple values (i.e. for list filter forms)
                    return $.param(parameters, true);
                },

                processResults: function (data) {
                    var element = this.$element[0];
                    $(element).children('option').attr('disabled', false);
                    var results = data.results;

                    results = results.reduce((results,record,idx) => {
                        record.text = resolvePath(record, element.getAttribute('display-field')) || record.name;
                        record.id = resolvePath(record, element.getAttribute('value-field')) || record.id;
                        if(element.getAttribute('disabled-indicator') && record[element.getAttribute('disabled-indicator')]) {
                            // The disabled-indicator equated to true, so we disable this option
                            record.disabled = true;
                        }

                        if( record.group !== undefined && record.group !== null && record.site !== undefined && record.site !== null ) {
                            results[record.site.name + ":" + record.group.name] = results[record.site.name + ":" + record.group.name] || { text: record.site.name + " / " + record.group.name, children: [] };
                            results[record.site.name + ":" + record.group.name].children.push(record);
                        }
                        else if( record.group !== undefined && record.group !== null ) {
                            results[record.group.name] = results[record.group.name] || { text: record.group.name, children: [] };
                            results[record.group.name].children.push(record);
                        }
                        else if( record.site !== undefined && record.site !== null ) {
                            results[record.site.name] = results[record.site.name] || { text: record.site.name, children: [] };
                            results[record.site.name].children.push(record);
                        }
                        else if ( (record.group !== undefined || record.group == null) && (record.site !== undefined || record.site === null) ) {
                            results['global'] = results['global'] || { text: 'Global', children: [] };
                            results['global'].children.push(record);
                        }
                        else {
                            results[idx] = record;
                        }
                        // DynamicGroupSerializer has a `children` field which fits an inappropriate if condition
                        // in select2.min.js, which will result in the incorrect rendering of DynamicGroup DynamicChoiceField.
                        // So we nullify the field here since we do not need this field.
                        if (record?.url ? record.url.includes("dynamic-groups") : false){
                            record.children = undefined;
                        }

                        return results;
                    },Object.create(null));

                    results = Object.values(results);

                    // Handle the null option, but only add it once
                    if (element.getAttribute('data-null-option') && data.previous === null) {
                        results.unshift({
                            id: 'null',
                            text: element.getAttribute('data-null-option')
                        });
                    }

                    // Check if there are more results to page
                    var page = data.next !== null;
                    return {
                        results: results,
                        pagination: {
                            more: page
                        }
                    };
                }
            }
        });
    });
}

// Flatpickr selectors
function initializeDateTimePicker(context){
    this_context = $(context);
    this_context.find('.date-picker').flatpickr({
        allowInput: true
    });
    this_context.find('.datetime-picker').flatpickr({
        allowInput: true,
        enableSeconds: true,
        enableTime: true,
        time_24hr: true
    });
    this_context.find('.time-picker').flatpickr({
        allowInput: true,
        enableSeconds: true,
        enableTime: true,
        noCalendar: true,
        time_24hr: true
    });
}

function initializeTags(context, dropdownParent=null){
    this_context = $(context);
    this_tag_field = this_context.find('#id_tags.tagfield')
    var tags = this_tag_field;
    if (tags.length > 0 && tags.val().length > 0){
        tags = this_tag_field.val().split(/,\s*/);
    } else {
        tags = [];
    }
    tag_objs = $.map(tags, function (tag) {
        return {
            id: tag,
            text: tag,
            selected: true
        }
    });
    // Replace the django issued text input with a select element
    this_tag_field.replaceWith('<select name="tags" id="id_tags" class="form-control tagfield"></select>');
    this_tag_field.select2({
        tags: true,
        data: tag_objs,
        multiple: true,
        allowClear: true,
        placeholder: "Tags",
        theme: "bootstrap",
        width: "off",
        dropdownParent: dropdownParent,
        ajax: {
            delay: 250,
            url: nautobot_api_path + "extras/tags/",

            data: function(params) {
                // Paging. Note that `params.page` indexes at 1
                var offset = (params.page - 1) * 50 || 0;
                var parameters = {
                    q: params.term,
                    limit: 50,
                    offset: offset,
                };
                return parameters;
            },

            processResults: function (data) {
                var results = $.map(data.results, function (obj) {
                    // If tag contains space add double quotes
                    if (/\s/.test(obj.name))
                    obj.name = '"' + obj.name + '"'

                    return {
                        id: obj.name,
                        text: obj.name
                    }
                });

                // Check if there are more results to page
                var page = data.next !== null;
                return {
                    results: results,
                    pagination: {
                        more: page
                    }
                };
            }
        }
    });
    this_tag_field.closest('form').submit(function(event){
        // django-taggit can only accept a single comma seperated string value
        // TODO(bryan): the element find here should just be event.target
        var value = $('#id_tags.tagfield').val();
        if (value.length > 0){
            var final_tags = value.join(', ');
            $('#id_tags.tagfield').val(null).trigger('change');
            var option = new Option(final_tags, final_tags, true, true);
            $('#id_tags.tagfield').append(option).trigger('change');
        }
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

function initializeMultiValueChar(context, dropdownParent=null){
    this_context = $(context);
    this_context.find('.nautobot-select2-multi-value-char').select2({
        allowClear: true,
        tags: true,
        theme: "bootstrap",
        placeholder: "---------",
        multiple: true,
        dropdownParent: dropdownParent,
        width: "off",
        "language": {
            "noResults": function(){
                return "Type something to add it as an option";
            }
        },
    });
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
    this_context = $(context);
    this_context.find('#select_all').click(function() {
        if ($(this).is(':checked')) {
            $('#select_all_box').find('button').prop('disabled', '');
        } else {
            $('#select_all_box').find('button').prop('disabled', 'disabled');
        }
    });
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
    initializeStaticChoiceSelection(this_context)
    initializeCheckboxes(this_context)
    initializeSlugField(this_context)
    initializeAutoPopulateField(this_context)
    initializeFormActionClick(this_context)
    initializeBulkEditNullification(this_context)
    initializeColorPicker(this_context)
    initializeDynamicChoiceSelection(this_context)
    initializeDateTimePicker(this_context)
    initializeTags(this_context)
    initializeVLANModeSelection(this_context)
    initializeSortableList(this_context)
    initializeImagePreview(this_context)
    initializeDynamicFilterForm(this_context)
    initializeSelectAllForm(this_context)
    initializeMultiValueChar(this_context)

    $(this_context).find(".modal").each(function() {
        const this_modal = $(this)
        initializeStaticChoiceSelection(this_modal, this_modal)
        initializeColorPicker(this_modal, this_modal)
        initializeDynamicChoiceSelection(this_modal, this_modal)
        initializeTags(this_modal, this_modal)
        initializeMultiValueChar(this_modal, this_modal)
    })
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

