import Head from 'next/head'
import Menu from "../common/components/menu"
import { Container } from "react-bootstrap";


export default function Home({children}) {
  return (
    <div className="">
      <Head>
        <title>Nautobot</title>
        <link rel="icon" href={process.env.NEXT_PUBLIC_NAUTOBOT_STATIC_ROOT + "/img/favicon.ico"} />
      </Head>
      <Menu />
      <Container fluid="sm" className='page-container'>
        {children}
      </Container>

      <footer>
      </footer>

      <style jsx>{`
        .page-container {
          margin-top: 2000px !important;
        }
        `}
        
      </style>
    </div>
  )
}
