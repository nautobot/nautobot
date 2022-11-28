import { useEffect, useState } from "react"
import { Container } from "react-bootstrap";
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import NavDropdown from 'react-bootstrap/NavDropdown';
import { axios_instance } from "@utils/utils";

export default function Menu() {
    const [NavMenu, setNavMenu] = useState([])
    useEffect(async () => {
        const nav_api = await axios_instance.get("/api/get-menu/")
        setNavMenu(nav_api.data)
    }, [])

    return (
        <Navbar bg="light" expand="lg" fixed="top">
            <Container fluid>
                <Navbar.Brand href="/">
                    <img
                        src={process.env.NEXT_PUBLIC_NAUTOBOT_STATIC_ROOT + "/img/nautobot_logo.svg"}
                        alt="nautobot-logo"
                        width={100}
                    />
                </Navbar.Brand>
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
                                                        <NavDropdown.Item style={{ "fontSize": "13px" }} key={menu_idx} href={menu[0]}>
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
        </Navbar>
    )
}
