/**
 * Bulk Delete Button Enhancement
 * 
 * Provides progressive enhancement for bulk delete buttons.
 * Without JavaScript: buttons work normally.
 * With JavaScript: buttons are disabled until items are selected, with helpful tooltips
 * 
 * Usage:
 * Add class 'btn-bulk-delete' to any bulk delete button with these data attributes:
 * - data-text: Text for single item (e.g., "Remove from cluster"). Fallback to button text.
 * - data-text-plural: Text for multiple items with {count} placeholder (e.g., "Remove from 3 clusters"). Fallback to data-text.
 * - data-help-msg: Tooltip text when disabled (e.g., "Select a cluster to remove device from"). Fallback to "Select items to delete".
 */

function initializeBulkDeleteButtons(context = document) {
    $(context).find('.btn-bulk-delete').each(function() {
        const btn = $(this);
        const table = btn.closest('form').find('table');
        if (!table.length || btn.data('bulk-delete-initialized')) return;        
        btn.data('bulk-delete-initialized', true);
        
        const helpMsg = btn.data('help-msg') || 'Select items to delete';
        const singularText = btn.data('text') || btn.text().trim();
        const pluralText = btn.data('text-plural') || singularText;
        
        // Set initial state to disabled with help message
        btn.prop('disabled', true).attr('title', helpMsg).tooltip();
        
        table.on('change.bulk-delete', 'input:checkbox', function() {
            const count = table.find('input:checkbox[name=pk]:checked').length;
            const text = count > 1 ? pluralText.replace('{count}', count) : singularText;
            
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