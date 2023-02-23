import { Container, Nav, Navbar, NavDropdown } from "react-bootstrap"
import { faSignIn, faSignOut } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Link, NavLink } from "react-router-dom"
import {useState, useEffect} from "react"
import useSWR from "swr"

import { nautobot_url } from "src/index"


const fetcher = (url) => fetch(url, { credentials: "include" }).then((res) => {
  if(res.status !== 200){
    throw new Error(res.json());
  }
  return res.json();
});

export default function BSNavBar() {
  const { data, error } = useSWR(nautobot_url + "/api/get-menu/", fetcher)
  const { data: profileData, error: profileError } = useSWR(nautobot_url + "/api/users/users/my-profile/", fetcher)
  const [ isLoggedIn, setIsLoggedIn] = useState(false)
  useEffect(() => {
    setIsLoggedIn(profileData ? true : false)
  }, [profileData, profileError, isLoggedIn]);
  if (error) return <div>Failed to load menu</div>
  if (!data) return <></>

  return (
    <Navbar bg="light" expand="lg" fixed="top">
      <Container fluid>
        <Link to="/">
          <Navbar.Brand>
            <img src={nautobot_url + "/static/img/nautobot_logo.svg"} alt="nautobot-logo" height={30} />
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
                            <NavDropdown.Item style={{ "fontSize": "13px" }} to={menu[0]} key={menu_idx} as={NavLink}>
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
        <Navbar.Collapse className="justify-content-end">
          <Navbar.Text>
            {
                isLoggedIn ?
                    <Link to="/logout/" onClick={() => setIsLoggedIn(false)}>
                      <FontAwesomeIcon icon={faSignOut} />
                      {" Logout"}
                    </Link>
                :
                    <Link to="/login/">
                      <FontAwesomeIcon icon={faSignIn} />
                      {" Login"}
                    </Link>
            }
          </Navbar.Text>
        </Navbar.Collapse>
      </Container>
    </Navbar >
  )
}
