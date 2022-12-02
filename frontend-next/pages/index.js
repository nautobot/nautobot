import Head from 'next/head'
import Layout from "../components/layout"
import 'bootstrap/dist/css/bootstrap.css'


export const nautobot_url = "http://localhost:8080"
export const nautobot_static = nautobot_url + "/static"

export default function Home() {
  return (
    <div>
      <Head>
        <title>Nautobot</title>
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <Layout />
    </div>
  )
}
