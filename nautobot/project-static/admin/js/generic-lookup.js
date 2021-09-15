/*
Generic content type object lookups in admin


Copyright (c) 2013, Jacob Magnusson
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
       this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.

    3. Neither the name of django-imagekit nor the names of its contributors
       may be used to endorse or promote products derived from this software
       without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


NOTE 1: This script requires some data attributes to be set on the option
        elements of the content_type select box. Setting the
        GenericContentTypeSelect widget on content_type fields in admin
        ensures that, and automatically includes this script.
NOTE 2: Requires an up-to-date jQuery, at least 1.8 (because of $.parseHTML use)

TODO 1: Enable multiple content_type / object_id fields on one change page
TODO 2: Don't presume the object id field's name attribute is `object_id`

*/
(function($) {
    $(document).ready(function() {
        var gettext = window.gettext || function(s) { return s; };
        var $contentTypeField = $('[data-generic-lookup-enabled=yes]')
                                              .parents('select:first');
        var $objectIdField = $('[name=object_id]');
        var $lookupBox = $('<a>')
                .append('<i class="glyphicon glyphicon-th-list" style="margin-left: 6px"></i>')
                .attr({
                    id: 'lookup_' + $objectIdField.attr('id'),
                    title: gettext('Browse')
                });
        var $lookedUpItem = $('<a>').attr({
            style: 'margin-left: 6px;',
            target: '_blank',
            title: gettext('Click to open the item in a new tab')
        });
        var objectIdVal = '';
        var newIdVal = '';
        var intervalId = null;

        var lookupSelected = function(url) {
            var newIdVal = $objectIdField.val();
            if (newIdVal === objectIdVal) {
                return;
            }
            $lookedUpItem.text('').attr('href', '');
            objectIdVal = newIdVal;

            if (newIdVal) {
                parseDetailPageXHR(url, newIdVal);
            }
        };

        var onContentTypeChange = function(e, extraArgs) {
            if ((extraArgs || {}).noClear !== true) {
                $objectIdField.val('');
            }
            var $selected = $(this).find(':selected:first');
            var url = $selected.attr('data-admin-url');
            $lookupBox.attr('href', $selected.attr('data-admin-url'));
            if (intervalId !== null) {
                window.clearInterval(intervalId);
            }
            intervalId = window.setInterval(function() {
                lookupSelected(url);
            }, 100);
            $lookupBox.on('click', function() {
                return window.showRelatedObjectLookupPopup(this);
            });
        };

        var parseDetailPageXHR = function(url, newVal) {
            var detailPageURL = url + newVal + '/';
            $.get(detailPageURL).done(function(responseText) {
                var html = $.parseHTML(responseText);
                $.each(html, function(i, el) {
                    if ((el.className || '').indexOf('container') === -1) { return; }
                    $lookedUpItem.text(($(el).find('.breadcrumb li:last').text() || ''));
                    $lookedUpItem.attr('href', detailPageURL);
                    return false;
                });
            });
        };

        $objectIdField.after($lookupBox);
        $lookupBox.after($lookedUpItem);
        $contentTypeField.on('change', onContentTypeChange)
                         .trigger('change', {noClear: true});
    });
})(jQuery);
