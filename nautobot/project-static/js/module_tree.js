document.addEventListener('DOMContentLoaded', function () {
    function toggleChildren(bayPk, show) {
        var children = document.querySelectorAll('[data-parent-bay="' + bayPk + '"]');
        children.forEach(function (row) {
            row.style.display = show ? '' : 'none';
            var childBay = row.dataset.bayPk;
            if (childBay) {
                toggleChildren(childBay, show);
            }
        });
    }

    document.querySelectorAll('.module-tree-toggle').forEach(function (toggle) {
        toggle.addEventListener('click', function (e) {
            e.preventDefault();
            var bayPk = toggle.dataset.bayPk;
            var icon = toggle.querySelector('.mdi');
            if (icon.classList.contains('mdi-chevron-down')) {
                icon.classList.remove('mdi-chevron-down');
                icon.classList.add('mdi-chevron-right');
                toggleChildren(bayPk, false);
            } else {
                icon.classList.remove('mdi-chevron-right');
                icon.classList.add('mdi-chevron-down');
                toggleChildren(bayPk, true);
            }
        });
    });

    var expandAll = document.getElementById('module-tree-expand-all');
    if (expandAll) {
        expandAll.addEventListener('click', function () {
            document.querySelectorAll('tr[data-parent-bay]').forEach(function (row) {
                row.style.display = '';
            });
            document.querySelectorAll('.module-tree-toggle .mdi').forEach(function (icon) {
                icon.classList.remove('mdi-chevron-right');
                icon.classList.add('mdi-chevron-down');
            });
        });
    }

    var collapseAll = document.getElementById('module-tree-collapse-all');
    if (collapseAll) {
        collapseAll.addEventListener('click', function () {
            document.querySelectorAll('tr[data-parent-bay]').forEach(function (row) {
                row.style.display = 'none';
            });
            document.querySelectorAll('.module-tree-toggle .mdi').forEach(function (icon) {
                icon.classList.remove('mdi-chevron-down');
                icon.classList.add('mdi-chevron-right');
            });
        });
    }
});
