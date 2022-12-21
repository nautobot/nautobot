import ListViewTemplate from "./BSListViewTemplate"
import { nautobot_url } from "../index"
import { useParams } from "react-router-dom"

export default function BSListView({ list_url }) {
  const { app_name, model_name } = useParams()
  // TODO: Restore page titles
  // let pagetitle = "Nautobot"
  // if (model_name) {
  //   pagetitle = model_name.replace("-", " ")
  //   pagetitle = pagetitle[0].toUpperCase() + pagetitle.slice(1)
  // }
  if (!app_name || !model_name) {
    return <></>
  }
  if (!list_url) {
    list_url = `${nautobot_url}/api/${app_name}/${model_name}/`
  }
  console.log(list_url)
  return (
    <ListViewTemplate list_url={list_url} />
  )
}
