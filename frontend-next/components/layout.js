import { Alert } from "react-bootstrap"
import Container from "react-bootstrap/Container"
import Menu from "./menu"
import { useRouter } from "next/router"

export default function Layout({ children }) {
  const router = useRouter()
  return (
    <>
      <Menu />
      <Container fluid="sm" className='page-container'>
        <Alert>
          Current route is {router.pathname}
        </Alert>
        {children}
      </Container>
      <footer>
      </footer>
    </>
  )
}
