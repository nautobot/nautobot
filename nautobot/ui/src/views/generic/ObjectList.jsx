import { useParams } from "react-router-dom"
import { Text } from "@nautobot/nautobot-ui"

import ListViewTemplate from "@views/BSListViewTemplate"


export default function BSListView({ list_url }) {
  const { app_name, model_name } = useParams()
  // TODO: Restore page titles
  // let pagetitle = "Nautobot"
  // if (model_name) {
  //   pagetitle = model_name.replace("-", " ")
  //   pagetitle = pagetitle[0].toUpperCase() + pagetitle.slice(1)
  // }
  if (!app_name || !model_name) {
    return <Text>Loading...</Text>
  }
  if (!list_url) {
    list_url = `/api/${app_name}/${model_name}/`
  }
  return (
    <ListViewTemplate list_url={list_url} />
  )
}
