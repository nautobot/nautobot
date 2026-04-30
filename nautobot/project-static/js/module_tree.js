$(document).ready(function () {
    function toggleChildren(bayPk, show) {
        var children = $('[data-parent-bay="' + bayPk + '"]');
        children.each(function () {
            if (show) {
                $(this).show();
            } else {
                $(this).hide();
            }
            var childBay = $(this).data('bay-pk');
            if (childBay) {
                toggleChildren(childBay, show);
            }
        });
    }

    $('.module-tree-toggle').click(function (e) {
        e.preventDefault();
        var bayPk = $(this).data('bay-pk');
        var icon = $(this).find('.mdi');
        if (icon.hasClass('mdi-chevron-down')) {
            icon.removeClass('mdi-chevron-down').addClass('mdi-chevron-right');
            toggleChildren(bayPk, false);
        } else {
            icon.removeClass('mdi-chevron-right').addClass('mdi-chevron-down');
            toggleChildren(bayPk, true);
        }
    });

    $('#module-tree-expand-all').click(function () {
        $('tr[data-parent-bay]').show();
        $('.module-tree-toggle .mdi').removeClass('mdi-chevron-right').addClass('mdi-chevron-down');
    });

    $('#module-tree-collapse-all').click(function () {
        $('tr[data-parent-bay]').hide();
        $('.module-tree-toggle .mdi').removeClass('mdi-chevron-down').addClass('mdi-chevron-right');
    });
});
