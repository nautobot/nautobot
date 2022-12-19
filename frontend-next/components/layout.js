import Container from "react-bootstrap/Container"
import Menu from "./menu"

export default function Layout({ children }) {
  return (
    <>
      <Menu />
      <Container fluid="sm" className='page-container'>
        {children}
      </Container>
      <footer>
      </footer>
    </>
  )
}
