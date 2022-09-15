import axios from "axios";


const axios_instance = axios.create({
    baseURL: process.env["NEXT_PUBLIC_NAUTOBOT_BASE_API_URL"],
})
axios_instance.defaults.headers["Authorization"] = "Token 991aebf2bf8e9b8e68988756e089a5ee27910147"

export {axios_instance}