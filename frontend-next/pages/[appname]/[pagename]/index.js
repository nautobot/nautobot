import Head from "next/head"
import ListViewTemplate from "components/list"
import Layout from "components/layout"
import { nautobot_url } from "pages"
import { useRouter } from "next/router"

export default function ListView() {
  const router = useRouter()
  const { appname, pagename } = router.query
  let pagetitle = "Nautobot"
  if (pagename) {
    pagetitle = pagename.replace("-", " ")
    pagetitle = pagetitle[0].toUpperCase() + pagetitle.slice(1)
  }
  if (!appname || !pagename) {
    return <></>
  }
  return (
    <div>
      <Head>
        <title>{pagetitle} - Nautobot</title>
        <link rel="icon" href="/static/favicon.ico" />
      </Head>
      <Layout>
        <ListViewTemplate list_url={`${nautobot_url}/api/${appname}/${pagename}/`} />
      </Layout>
    </div>
  )
}
