// Interface filtering
document.querySelectorAll('input.interface-filter').forEach(input => {
    input.addEventListener('input', function() {
        const filter = new RegExp(this.value);
        const rows = document.querySelectorAll('table > tbody > tr');
        const toggleChecked = document.querySelector('input.toggle')?.checked || false;

        rows.forEach(row => {
            const name = row.getAttribute('data-name') || '';
            const checkbox = row.querySelector('input[type="checkbox"][name="pk"]');

            if (filter.test(name)) {
                if (checkbox) checkbox.checked = toggleChecked;
                row.style.display = '';
            } else {
                if (checkbox) checkbox.checked = false;
                row.style.display = 'none';
            }
        });
    });
});