import ListView from "pages/[appname]/[pagename]"
import { nautobot_url } from "pages/_app"
import { useRouter } from "next/router"

export default function PluginListView() {
  const router = useRouter()
  const { appname, pagename } = router.query
  if (!appname || !pagename) return <></>
  const list_url = `${nautobot_url}/api/plugins/${appname}/${pagename}/`
  return (
    <ListView list_url={list_url} />
  )
}
