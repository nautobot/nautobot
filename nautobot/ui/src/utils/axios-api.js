// TODO this may no longer be needed but might be a nice library too so should be shored up
import axios from "axios"

import { API_USER_SESSION_INFO } from "@constants/apiPath"

axios.defaults.withCredentials = true
axios.defaults.xsrfCookieName = 'csrftoken'
axios.defaults.xsrfHeaderName = 'X-CSRFToken'

export default function getApiClient() {

    let session_info = {}
    
    let client = {}
    
    axios.get(API_USER_SESSION_INFO).then((resp) => { session_info = resp.data })

    return client
}