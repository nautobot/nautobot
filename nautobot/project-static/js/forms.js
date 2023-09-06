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
    // "Toggle" checkbox for object lists (PK column)
    this_context.find('input:checkbox.toggle').click(function() {
        $(this).closest('table').find('input:checkbox[name=pk]:visible').prop('checked', $(this).prop('checked'));

        // Show the "select all" box if present
        if ($(this).is(':checked')) {
            $('#select_all_box').removeClass('hidden');
        } else {
            $('#select_all').prop('checked', false);
        }
    });

    // Uncheck the "toggle" and "select all" checkboxes if an item is unchecked
    this_context.find('input:checkbox[name=pk]').click(function (event) {
        if (!$(this).attr('checked')) {
            $('input:checkbox.toggle, #select_all').prop('checked', false);
        }
    });
}

function initializeSlugField(context){
    this_context = $(context);
    var slug_field = this_context.find('#id_slug');
    // If id_slug field is not to be found
    // check if it is rename to key field like what we did for CustomField and Relationship
    if (slug_field.length == 0) {
        slug_field = this_context.find('#id_key');
    }
    if (slug_field.length != 0) {
        var slug_source_arr = slug_field.attr('slug-source').split(" ");
        var slug_length = slug_field.attr('maxlength');
        if (slug_field.val()) {
            slug_field.attr('_changed', true);
        }
        slug_field.change(function() {
            $(this).attr('_changed', true);
        });
        function reslugify() {
            let slug_str = "";
            for (slug_source_str of slug_source_arr) {
                if (slug_str != "") {
                    slug_str += " ";
                }
                let slug_source = $('#id_' + slug_source_str);
                slug_str += slug_source.val();
            }
            slug_field.val(slugify(slug_str, (slug_length ? slug_length : 100)));
        };

        for (slug_source_str of slug_source_arr) {
            let slug_source = $('#id_' + slug_source_str);
            slug_source.on('keyup change', function() {
                if (slug_field && !slug_field.attr('_changed')) {
                    reslugify();
                }
            });
        }
        this_context.find('button.reslugify').click(reslugify);
    }
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

// Dynamic Choice Selection
function initializeDynamicChoiceSelection(context, dropdownParent=null){
    this_context = $(context);
    this_context.find('.nautobot-select2-api').each(function(){
        thisobj = $(this);
        placeholder = thisobj.attr("data-null-option") || "---------";
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
                        record.text = record[element.getAttribute('display-field')] || record.name;
                        record.id = record[element.getAttribute('value-field')] || record.id;
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
        let query_params = location.search;
        let type = $(this).attr("data-field-type");
        let field_value = $(this).attr("data-field-value");
        let query_string = location.search.substr(1).split("&");

        if (type === "parent") {
            query_string = query_string.filter(item => item.search(field_value) < 0);
        } else {
            let parent = $(this).attr("data-field-parent");
            query_string = query_string.filter(item => item.search(parent + "=" + field_value) < 0)
        }
        location.replace("?" + query_string.join("&"))
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

        // Get the serialize data from the forms and filter out query_params which values are empty e.g ?sam=&dan=2 becomes dan=2
        let dynamic_filter_form_query = $("#dynamic-filter-form").serialize().split("&").filter(params => params.split("=")[1].length)
        let default_filter_form_query = $("#default-filter form").serialize().split("&").filter(params => params.split("=")[1].length)
        // Union Operation
        let search_query = [...new Set([...default_filter_form_query, ...dynamic_filter_form_query])].join("&")
        location.replace("?" + search_query)
    })

    // On submit of filter search form
    this_context.find("#search-form").on("submit", function(e){
        // Since the Dynamic Filter Form will already grab my q field, just have it do a majority of the work.
        e.preventDefault()
        $("#dynamic-filter-form").submit()
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
    this_context = $(context);
    initializeStaticChoiceSelection(this_context)
    initializeCheckboxes(this_context)
    initializeSlugField(this_context)
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
        this_modal = $(this)
        initializeStaticChoiceSelection(this_modal, this_modal)
        initializeColorPicker(this_modal, this_modal)
        initializeDynamicChoiceSelection(this_modal, this_modal)
        initializeTags(this_modal, this_modal)
        initializeMultiValueChar(this_modal, this_modal)
    })
}

function jsify_form(context) {
    this_context = $(context);
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


$(document).ready((e) => {
    jsify_form(this.document);
    initializeResultPerPageSelection(this.document);
})

// Scroll up an offset equal to the first nav element if a hash is present
// Cannot use '#navbar' because it is not always visible, like in small windows
function headerOffsetScroll() {
    if (window.location.hash) {
        // Short wait needed to allow the page to scroll to the element
        setTimeout(function() {
            window.scrollBy(0, -$('nav').height())
        }, 10);
    }
}

// Account for the header height when hash-scrolling
window.addEventListener('load', headerOffsetScroll);
window.addEventListener('hashchange', headerOffsetScroll);
