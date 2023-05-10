export function toTitleCase(str, separator = " ") {
    return str
        .split(separator)
        .map((x) => (x ? x[0].toUpperCase() + x.slice(1) : ""))
        .join(" ");
}

export function slugify(str) {
    let data = str.replace(/^\s+|\s+$/g, ""); // trim
    data = data.toLowerCase();

    // Remove accents, swap ñ for n, etc
    var from = "àáäâèéëêìíïîòóöôùúüûñç·/_,:;";
    var to = "aaaaeeeeiiiioooouuuunc------";
    for (var i = 0, l = from.length; i < l; i++) {
        data = data.replace(new RegExp(from.charAt(i), "g"), to.charAt(i));
    }

    data = data
        .replace(/[^a-z0-9 -]/g, "") // remove invalid chars
        .replace(/\s+/g, "-") // collapse whitespace and replace by -
        .replace(/-+/g, "-") // collapse dashes
        .replace(/_+/g, "-"); // replace underscores with hyphens

    return data;
}
