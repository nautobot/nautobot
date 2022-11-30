import { useEffect, useState } from "react"
import { Container } from "react-bootstrap";
import Nav from "react-bootstrap/Nav";
import Navbar from "react-bootstrap/Navbar";
import NavDropdown from "react-bootstrap/NavDropdown";
import API from "common/utils/utils";
import { LinkContainer } from "react-router-bootstrap";
import nautobot_static from "index";

export default function Menu() {
    const [NavMenu, setNavMenu] = useState([])
    useEffect(() => {
        async function fetchData() {
            const nav_api = await API.get("/api/get-menu/")
            setNavMenu(nav_api.data)
        };
        fetchData();
    }, [])

    return (
        <Navbar bg="light" expand="lg" fixed="top">
            <Container fluid>
                <LinkContainer to="/">
                    <Navbar.Brand>
                        <img
                            src={nautobot_static() + "/img/nautobot_logo.svg"}
                            alt="nautobot-logo"
                            width={100}
                        />
                    </Navbar.Brand>
                </LinkContainer>
                <Navbar.Toggle aria-controls="basic-navbar-nav" />
                <Navbar.Collapse id="basic-navbar-nav">
                    <Nav className="me-auto">
                        {
                            NavMenu.map((item, idx) => (
                                <NavDropdown key={idx} title={item.name} id="basic-nav-dropdown" style={{ "fontSize": "14px" }}>
                                    {
                                        Object.entries(item.properties.groups).map((group, group_idx) => (
                                            <div key={group_idx}>
                                                {
                                                    Object.entries(group[1].items).map((menu, menu_idx) => (
                                                        <LinkContainer to={menu[0]} key={menu_idx}>
                                                            <NavDropdown.Item style={{ "fontSize": "13px" }}>
                                                                {menu[1].name}
                                                            </NavDropdown.Item>
                                                        </LinkContainer>
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
        </Navbar>
    )
}
