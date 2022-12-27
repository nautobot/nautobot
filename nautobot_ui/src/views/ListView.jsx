import ListTemplate from "@nautobot/layouts/ListTemplate"
import { useParams } from "react-router-dom"


export default function ListView({ match, location }) {
    const { model_name } = useParams()

    return (
        <ListTemplate  page_title={model_name.capitalize()} />
    )
}