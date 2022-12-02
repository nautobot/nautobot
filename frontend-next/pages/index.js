import Head from 'next/head'
import Layout from "../components/layout"
import 'bootstrap/dist/css/bootstrap.css'


export const nautobot_static = "/nautobot_static"

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
