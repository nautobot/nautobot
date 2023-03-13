import { Alert, Container } from "@chakra-ui/react"  // TODO import from nautobot-ui when available
import { useLocation } from "react-router-dom"

import Menu from "@components/common/BSNavBar"


export default function Layout({ children }) {
  let location = useLocation();
  return (
    <>
      <Menu />
      <Container fluid="sm" className='page-container'>
        <Alert status='info'>
          Current route is {location.pathname}
        </Alert>
        {children}
      </Container>
      <footer>
      </footer>
    </>
  )
}
