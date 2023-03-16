import { Alert, Container } from "@chakra-ui/react"
import { useLocation } from "react-router-dom"

import Menu from "@components/common/BSNavBar"
import { fetchSessionAsync } from "@utils/session";



export default function Layout({ children }) {
  let location = useLocation();

  fetchSessionAsync()
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
