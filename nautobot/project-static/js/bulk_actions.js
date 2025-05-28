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
        
        // Set initial state to disabled with help message
        btn.prop('disabled', true).attr('title', helpMsg).tooltip();
        
        form.on('change.bulk-delete', 'input:checkbox', function() {
            const count = form.find('input:checkbox[name=pk]:checked').length;
            const text = count > 1 ? label.replace('{count}', count) : label;
            
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