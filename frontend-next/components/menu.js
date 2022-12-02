import Container from "react-bootstrap/Container"
import Link from "next/link"
import Nav from "react-bootstrap/Nav"
import Navbar from "react-bootstrap/Navbar"
import NavDropdown from "react-bootstrap/NavDropdown"
import useSWR from "swr"
import { nautobot_static, nautobot_url } from "pages/index"

const fetcher = (url) => fetch(url, { credentials: "include" }).then((res) => res.json());

export default function Menu() {
  const { data, error } = useSWR(nautobot_url + "/api/get-menu/", fetcher)
  if (error) return <div>Failed to load menu</div>
  if (!data) return <></>

  return (
    <Navbar bg="light" expand="lg" fixed="top">
      <Container fluid>
        <Link href="/" passHref>
          <Navbar.Brand>
            <img
              src={nautobot_static + "/img/nautobot_logo.svg"}
              alt="nautobot-logo"
              height={30}
            />
          </Navbar.Brand>
        </Link>
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            {
              data.map((item, idx) => (
                <NavDropdown key={idx} title={item.name} id="basic-nav-dropdown" style={{ "fontSize": "14px" }}>
                  {
                    Object.entries(item.properties.groups).map((group, group_idx) => (
                      <div key={group_idx}>
                        <NavDropdown.Header>{group[0]}</NavDropdown.Header>
                        {
                          Object.entries(group[1].items).map((menu, menu_idx) => (
                            <NavDropdown.Item style={{ "fontSize": "13px" }} href={menu[0]} key={menu_idx} as={Link}>
                              {menu[1].name}
                            </NavDropdown.Item>
                          ))
                        }
                        <NavDropdown.Divider />
                      </div>
                    ))
                  }
                </NavDropdown>
              ))
            }
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar >
  )
}
