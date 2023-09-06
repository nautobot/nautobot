export function toTitleCase(str, separator = " ") {
    return str
        .split(separator)
        .map((x) => (x ? x[0].toUpperCase() + x.slice(1) : ""))
        .join(" ");
}
