/**
 * Bulk Delete Button Enhancement
 * 
 * Provides progressive enhancement for bulk delete buttons.
 * Without JavaScript: buttons work normally.
 * With JavaScript: buttons are disabled until items are selected, with helpful tooltips
 * 
 * Usage:
 * Add class 'btn-bulk-delete' to any bulk delete button with these data attributes:
 * - data-form-id: ID of the form containing the checkbox inputs. This is required.
 * - data-help-msg: Tooltip text when disabled (e.g., "Select a cluster to remove device from"). Fallback to "Select items to delete".
 * - data-label-checked-single: Button text for single item (e.g., "Remove from cluster"). Fallback to button text.
 * - data-label-checked-multiple: Button text for multiple items with [count] placeholder (e.g., "Remove from 3 clusters"). Fallback to data-label-checked-single.
 */

function initializeBulkDeleteButtons(context = document) {
    $(context).find('.btn-bulk-delete').each(function() {
        const btn = $(this);
        const form = $('#' + btn.data('form-id'));
        if (!form.length) {
            console.log('No form found for button', btn);
            return;
        };
        btn.data('bulk-delete-initialized', true);
        
        const helpMsg = btn.data('help-msg') || 'Select items to delete';
        const label = btn.text().trim();
        const labelCheckedSingle = btn.data('label-checked-single') || label;
        const labelCheckedMultiple = btn.data('label-checked-multiple') || label;
        
        // Set initial state to disabled with help message
        btn.prop('disabled', true).attr('title', helpMsg).tooltip();
        
        form.on('change.bulk-delete', 'input:checkbox', function() {
            const count = form.find('input:checkbox[name=pk]:checked').length;
            let text;
            switch (count) {
                case 0:
                    text = label;
                    break;
                case 1:
                    text = labelCheckedSingle.replace('[count]', count);
                    break;
                default:
                    text = labelCheckedMultiple.replace('[count]', count);
            }
            
            btn.prop('disabled', !count)
               .tooltip('destroy')
               .html(btn.find('span.mdi').clone().prop('outerHTML') + ' ' + text + ' ');
            
            if (!count) {
                btn.attr('title', helpMsg).tooltip();
            }
        });
    });
}

$(document).ready(function() {
    initializeBulkDeleteButtons();
});

// Make available globally for dynamic content
window.initializeBulkDeleteButtons = initializeBulkDeleteButtons; 