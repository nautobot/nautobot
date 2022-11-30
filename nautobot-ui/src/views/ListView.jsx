import BaseLayout from "@layouts/BaseLayout"
import { useEffect } from "react"
import { useParams } from "react-router-dom"

export default function ListView({ match, location}){
    const {app_name, model_name} = useParams()
    
    useEffect(() => {

    }, [app_name, model_name])
    
    return (
        <BaseLayout>
            <h1>ListBaseView</h1>
        </BaseLayout>
    )
}