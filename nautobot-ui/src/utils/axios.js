import axios from "axios";


const naxios = axios.create({
    baseURL: window.env["NAUTOBOT_BASE_API_URL"],
})
naxios.defaults.headers["Authorization"] = `Token ${window.env["NAUTOBOT_TOKEN"]}`

export {naxios};