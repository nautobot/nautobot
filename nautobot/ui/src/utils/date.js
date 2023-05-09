export function humanFriendlyDate(dateStr) {
    const date = new Date(dateStr);
    return (
        date.getFullYear().toString() +
        "-" +
        date.getMonth().toString().padStart(2, "0") +
        "-" +
        date.getDate().toString().padStart(2, "0") +
        " " +
        date.getHours().toString().padStart(2, "0") +
        ":" +
        date.getMinutes().toString().padStart(2, "0")
    );
}
