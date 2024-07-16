document.addEventListener("DOMContentLoaded", function() {
    // Select all header elements with the class "orderable" containing links
    const headers = document.querySelectorAll(".orderable a");

    headers.forEach(header => {
        // Get the column name from the data attribute
        const columnName = header.dataset.columnName;

        // Add a click event listener to each header
        header.addEventListener("click", function(event) {
            // Prevent the default link behavior
            event.preventDefault();

            // Get the current URL and its search parameters
            const currentUrl = new URL(window.location.href);
            const searchParams = currentUrl.searchParams;
            let sortParam = searchParams.get("sort");

            if (sortParam === columnName) {
                // If the column is already sorted in ascending order, switch to descending
                searchParams.set("sort", "-" + columnName);
            } else if (sortParam === "-" + columnName) {
                // If the column is already sorted in descending order, reset to default
                searchParams.delete("sort");
                window.location.replace(window.location.pathname); // Reload the page with the default view without adding a new entry to history
                return;
            } else {
                // If no sort or default state, set to ascending
                searchParams.set("sort", columnName);
            }

            // Update the URL with the new sort parameter
            window.location.replace(window.location.pathname + "?" + searchParams.toString());
        });

        // Initialize the header with the appropriate sort state indicator
        const sortParam = new URLSearchParams(window.location.search).get("sort");
        if (sortParam === columnName) {
            // If sorted in ascending order, add an up arrow icon
            header.innerHTML += ' <i class="mdi mdi-arrow-up-thin"></i>';
        } else if (sortParam === `-${columnName}`) {
            // If sorted in descending order, add a down arrow icon
            header.innerHTML += ' <i class="mdi mdi-arrow-down-thin"></i>';
        }
    });
});
