import NautobotTable from "@core/Table"
import BaseLayout from "@layouts/BaseLayout"
import ListTemplate from "@layouts/ListTemplate"
import { naxios } from "@utils/axios"
import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"


export default function ListView({ match, location }) {
    const { app_name, model_name } = useParams()

    return (
        <ListTemplate 
            page_title={model_name.capitalize()}
            table_url=""
            table_data_url=""
        ></ListTemplate>
    )
}