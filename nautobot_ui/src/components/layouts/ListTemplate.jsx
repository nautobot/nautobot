import NautobotTable from "@core/Table"
import BaseLayout from "@layouts/BaseLayout"
import { naxios } from "@utils/axios"
import { useEffect, useState } from "react"


export default function ListTemplate({ page_title, table_head_url, table_data_url, buttons }) {
    const [table_head, set_table_head] = useState([])
    const [table_data, set_table_data] = useState([])
    const [extra_props, set_extra_props] = useState({})

    useEffect(() => {
        let current_path = window.location.pathname
        let table_body_endpoint = current_path.endsWith("/") ? current_path : current_path + "/"
        let table_head_endpoint = current_path + "table-fields/"
        
        if (table_head_url){
            table_head_endpoint=table_head_url
        }
        if(table_data_url){
            table_body_endpoint=table_data_url
        }
        
        async function getTableData(){
            set_table_data([])
            set_table_head([])
            
            let table_response = await naxios.get(table_head_endpoint)
            set_table_head(table_response.data.data)

            let table_body_response = await naxios.get(table_body_endpoint)
            set_table_data(table_body_response.data.results)
        }
        getTableData()

        if(buttons){
            set_extra_props(data => ({...data, "buttons": buttons}))
        }
    }, [page_title])

    return (
        <BaseLayout page_title={page_title}>
            <NautobotTable header_coloums={table_head} body_coloums={table_data} {...extra_props} />
        </BaseLayout>
    )
}