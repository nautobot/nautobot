/* Convert an API URL into its presumed UI equivalent */
export function uiUrl(apiUrl) {
    return apiUrl.replace("/api/", "/");
}

/* Build url from app_label, model_name and optional pk */
export function buildUrl(appLabel, modelName, pk = null, isPlugin = false) {
    let url = `/${appLabel}/${modelName}/`;
    if (isPlugin) {
        url = "/plugins" + url;
    }
    if (pk) {
        url += pk + "/";
    }
    return url;
}
