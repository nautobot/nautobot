/* Convert an API URL into its presumed UI equivalent */
export function uiUrl(apiUrl) {
    return apiUrl.replace("/api/", "/");
}

/* Build url form app_label, model_name and or pk */
export function buildUrl(appLabel, modelName, pk = null, isPlugin = false) {
    let url = `/${appLabel}/${modelName}/`;
    if (isPlugin) {
        url = "/plugin" + url;
    }
    if (pk) {
        url += pk + "/";
    }
    return url;
}
