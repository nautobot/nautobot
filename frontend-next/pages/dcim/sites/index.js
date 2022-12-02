import ListViewTemplate from "components/list"
import { nautobot_url } from "pages"

export default function ListView() {
    return (
        <ListViewTemplate list_url={nautobot_url + "/api/dcim/sites/"} />
    )
}
