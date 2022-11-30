
import React, { useState, useEffect } from 'react';
import { Link } from "react-router-dom";
import {
    MDBContainer,
    MDBNavbar,
    MDBNavbarBrand,
    MDBNavbarNav,
    MDBNavbarItem,
    MDBDropdown,
    MDBDropdownToggle,
    MDBDropdownMenu,
    MDBDropdownItem,
} from 'mdb-react-ui-kit';
import { naxios } from '@utils/axios';


export default function NavBar() {
    const [NavMenu, setNavMenu] = useState([])

    useEffect(() => {
        async function handleNavMenu() {
            const nav_api = await naxios.get("/get-menu/")
            setNavMenu(nav_api.data)
        }
        handleNavMenu()
    }, [])

    return (
        <MDBNavbar expand='lg' dark bgColor='dark'>
            <MDBContainer fluid>
                <MDBNavbarBrand href='#'>Nautobot</MDBNavbarBrand>
                <MDBNavbarNav className='me-auto mb-2 mb-lg-0'>
                    {
                        NavMenu.map((item, idx) => (
                            <MDBNavbarItem key={idx}>
                                <MDBDropdown>
                                    <MDBDropdownToggle tag='a' className='nav-link' role='button'>
                                        {item.name}
                                    </MDBDropdownToggle>
                                    <MDBDropdownMenu>
                                        {
                                            Object.entries(item.properties.groups).map((group, idx) => (
                                                <div key={idx}>
                                                    {
                                                        Object.entries(group[1].items).map((menu, idx) => (
                                                            <Link to={menu[0]} key={idx} className="dropdown-item-menu">
                                                                {menu[1].name}
                                                            </Link>
                                                        ))
                                                    }
                                                </div>

                                            ))
                                        }
                                    </MDBDropdownMenu>
                                </MDBDropdown>
                            </MDBNavbarItem>
                        ))
                    }
                </MDBNavbarNav>
            </MDBContainer>
        </MDBNavbar>
    );
}