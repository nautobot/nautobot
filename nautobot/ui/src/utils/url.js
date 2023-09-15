/* Convert an API URL into its presumed UI equivalent */
export function uiUrl(apiUrl) {
    return apiUrl.replace("/api/", "/");
}
