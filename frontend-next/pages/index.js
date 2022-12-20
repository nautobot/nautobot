import Head from "next/head"
import Home from "components/home"
import Layout from "components/layout"

export default function Index() {
  return (
    <div>
      <Head>
        <title>Nautobot</title>
        <link rel="icon" href="/static/favicon.ico" />
      </Head>
      <Layout>
        <Home />
      </Layout>
    </div>
  )
}
