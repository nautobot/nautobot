import axios from "axios";


const naxios = axios.create({
    baseURL: process.env["REACT_APP_NAUTOBOT_BASE_API_URL"],
})
naxios.defaults.headers["Authorization"] = `Token ${process.env["REACT_APP_NAUTOBOT_TOKEN"]}`

export {naxios};