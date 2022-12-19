import Head from 'next/head'
import Home from "components/home"
import Layout from "components/layout"
import 'bootstrap/dist/css/bootstrap.css'

const dev = process.env.NODE_ENV !== "production"
export const nautobot_url = dev ? "http://localhost:8080" : ""

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
