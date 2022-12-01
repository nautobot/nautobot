import ListViewLayout from "@components/layouts/ListViewLayout"
import { useEffect } from "react"
import { useParams } from "react-router-dom"


export default function ListView({ match, location }) {
    const { app_name, model_name } = useParams()

    useEffect(() => {

    }, [app_name, model_name])

    return (
        <ListViewLayout page_title={model_name.capitalize()}>
        </ListViewLayout>
    )
}