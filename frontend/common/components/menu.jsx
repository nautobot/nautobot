import axios from "axios";
import {useEffect, useState} from "react"
import { Container } from "react-bootstrap";
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import NavDropdown from 'react-bootstrap/NavDropdown';

export default function Menu() {
    const [NavMenu, setNavMenu] = useState([])
    useEffect(async () => {
        const nav_api = await (await axios.get(process.env.NEXT_PUBLIC_NAUTOBOT_BASE_URL + "/api/get-menu/")).data
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
                <ul class="nav navbar-nav">
                    <li class="dropdown">
                        <a 
                            href="#"
                            class="dropdown-toggle"
                            data-tab-weight="100"
                            data-toggle="dropdown"
                            role="button"
                            aria-haspopup="true"
                            aria-expanded="false"
                        >
                            Organization <span class="caret"></span>
                        </a>
                        <ul class="dropdown-menu">
                            <li class="dropdown-header" data-group-weight="100">Sites</li>
                            <li>
                                <div class="buttons pull-right">
                                    <a href="/dcim/sites/add/" data-button-weight="100" class="btn btn-xs btn-success" title="Add">
                                        <i class="mdi mdi-plus-thick"></i>
                                    </a>
                                    <a href="/dcim/sites/import/" data-button-weight="200" class="btn btn-xs btn-primary"
                                        title="Import">
                                        <i class="mdi mdi-database-import-outline"></i>
                                    </a>
                                </div>
                                <a href="/dcim/sites/" data-item-weight="100">
                                    Sites
                                </a>
                            </li>
                            <li>
                                <div class="buttons pull-right">
                                    <a href="/dcim/regions/add/" data-button-weight="100" class="btn btn-xs btn-success" title="Add">
                                        <i class="mdi mdi-plus-thick"></i>
                                    </a>
                                    <a href="/dcim/regions/import/" data-button-weight="200" class="btn btn-xs btn-primary"
                                        title="Import">
                                        <i class="mdi mdi-database-import-outline"></i>
                                    </a>
                                </div>
                                <a href="/dcim/regions/" data-item-weight="200">
                                    Regions
                                </a>
                            </li>
                            <li class="divider"></li>
                        </ul>
                    </li>
                </ul>
                    {/* <Nav className="me-auto">
                        {
                            NavMenu.map((item, idx) => (
                                <NavDropdown key={idx} title={item.name} id="basic-nav-dropdown">
                                    {
                                        Object.entries(item.properties.groups).map((child, child_idx) => (
                                            <NavDropdown.Item key={child_idx} href={child.link}>{child[0]}</NavDropdown.Item>
                                        ))
                                    }
                                </NavDropdown>
                            ))
                        }
                    </Nav> */}
                </Navbar.Collapse>
            </Container>
        </Navbar>
    )
}