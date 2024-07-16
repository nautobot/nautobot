document.addEventListener("DOMContentLoaded", function() {
    // Select all header elements with the class "orderable" containing links
    const headers = document.querySelectorAll(".orderable a");
    const clickCounts = {};

    headers.forEach(header => {
        // Get the column name from the data attribute
        const columnName = header.dataset.columnName;
        clickCounts[columnName] = 0;

        // Add a click event listener to each header
        header.addEventListener("click", function(event) {
            // Prevent the default link behavior
            event.preventDefault();

            // Increment the click count for the column
            clickCounts[columnName] += 1;

            // Get the current URL and its search parameters
            const currentUrl = new URL(window.location.href);
            const searchParams = new URLSearchParams(currentUrl.search);
            let sortParam = searchParams.get("sort");

            if (sortParam === columnName) {
                // If the column is already sorted in ascending order, switch to descending
                searchParams.set("sort", "-" + columnName);
            } else if (sortParam === "-" + columnName) {
                // If the column is already sorted in descending order, reset to default
                searchParams.delete("sort");
                window.location.href = window.location.pathname; // Reload the page with the default view
                return;
            } else {
                // If no sort or default state, set to ascending
                searchParams.set("sort", columnName);
            }

            // Update the URL with the new sort parameter
            window.location.search = searchParams.toString();
        });

        // Initialize the header with the appropriate sort state indicator
        const sortParam = new URLSearchParams(window.location.search).get("sort");
        if (sortParam === columnName) {
            // If sorted in ascending order, add an up arrow
            header.innerHTML += " &#8593;";
        } else if (sortParam === "-" + columnName) {
            // If sorted in descending order, add a down arrow
            header.innerHTML += " &#8595;";
        }
    });
});
