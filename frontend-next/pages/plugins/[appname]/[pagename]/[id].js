import ObjectRetrieve from "pages/[appname]/[pagename]/[id]";
import { nautobot_url } from "pages/_app"
import { useRouter } from "next/router"

export default function PluginObjectRetrieve() {
  const router = useRouter()
  const { appname, pagename, id } = router.query
  if (!appname || !pagename || !id) return <></>
  const api_url = `${nautobot_url}/api/plugins/${appname}/${pagename}/${id}/`
  return (
    <ObjectRetrieve api_url={api_url} />
  )
}
