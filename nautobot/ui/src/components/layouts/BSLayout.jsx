import { Alert, Container } from "@chakra-ui/react"
import { useLocation } from "react-router-dom"

import Menu from "@components/common/BSNavBar"


export default function Layout({ children }) {
  let location = useLocation();
  return (
    <>
      <Menu />
      <Container fluid="sm" className='page-container'>
        <Alert>
          Current route is {location.pathname}
        </Alert>
        {children}
      </Container>
      <footer>
      </footer>
    </>
  )
}
