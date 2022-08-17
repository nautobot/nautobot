import {useEffect, useState} from "react"
import { Container } from "react-bootstrap";
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import NavDropdown from 'react-bootstrap/NavDropdown';

export default function Menu() {
    const [NavMenu, setNavMenu] = useState([])
    useEffect(() => {
        const nav_api = require("../utils/nav_menu_api.json")
        setNavMenu(nav_api)
        
    }, [NavMenu])

    return (
        <Navbar bg="light" expand="lg" fixed="top">
            <Container>
                <Navbar.Brand href="/">
                    <img 
                        src={process.env.NEXT_PUBLIC_NAUTOBOT_STATIC_ROOT + "/img/nautobot_logo.svg"} 
                        alt="nautobot-logo" 
                        width={150}
                    />
                </Navbar.Brand>
                <Navbar.Toggle aria-controls="basic-navbar-nav" />
                <Navbar.Collapse id="basic-navbar-nav">
                    <Nav className="me-auto">
                        {
                            NavMenu.map((item, idx) => (
                                <NavDropdown key={idx} title={item.name} id="basic-nav-dropdown">
                                    {
                                        item.children.map((child, child_idx) => (
                                            <NavDropdown.Item key={child_idx} href={child.link}>{child.name}</NavDropdown.Item>
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