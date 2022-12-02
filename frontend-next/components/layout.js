import Alert from "react-bootstrap/Alert"
import Container from "react-bootstrap/Container"
import Menu from "./menu"

export default function Layout({ children }) {
  return (
    <>
      <Menu />
      <Container fluid="sm" className='page-container'>
        <Alert variant="success" style={{ textAlign: "center" }}>
          Example Plugin says “Hello, admin!” 👋 <br />
        </Alert>
        {children}
      </Container>
      <footer>
      </footer>
    </>
  )
}
