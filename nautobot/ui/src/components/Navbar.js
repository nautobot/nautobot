import { useSelector } from "react-redux";
import {
    Link as ReactRouterLink,
    NavLink as ReactRouterNavLink,
    useLocation,
} from "react-router-dom";
import {
    AutomationIcon,
    DcimIcon,
    Input,
    InputGroup,
    InputLeftElement,
    IpamIcon,
    Menu,
    MenuButton,
    MenuItem,
    MenuList,
    Navbar as UINavbar,
    NavbarMenuButton,
    NavbarSection,
    NavbarSections,
    PlatformIcon,
    SearchIcon,
    SecurityIcon,
} from "@nautobot/nautobot-ui";

import RouterButton from "@components/RouterButton";
import { useGetNewUIReadyRoutesQuery } from "@utils/api";
import { isRouteNewUIReady } from "@utils/navigation";
import {
    currentUserSelector,
    isLoggedInSelector,
    getCurrentContextSelector,
} from "@utils/store";
import { useEffect } from "react";

export function Navbar() {
    const isLoggedIn = useSelector(isLoggedInSelector);
    const currentContext = useSelector(getCurrentContextSelector);
    const currentUser = useSelector(currentUserSelector);
    const location = useLocation();
    const { data: readyRoutes } = useGetNewUIReadyRoutesQuery();

    // Check if current location is NewUIReady; if not redirect user back to legacy UI
    useEffect(() => {
        if (readyRoutes) {
            // Remove trailing `/`, as `isRouteNewUIReady` requires this.
            const path = location.pathname.replace(/^\/+/, "");
            if (!isRouteNewUIReady(path, readyRoutes)) {
                window.location.reload();
            }
        }
    }, [location, readyRoutes]);

    return (
        <UINavbar>
            <NavbarSections>
                {[
                    {
                        children: "Inventory",
                        leftIcon: <DcimIcon />,
                        to: "/dcim/devices/",
                    },
                    {
                        children: "Networks",
                        leftIcon: <IpamIcon />,
                        to: "/ipam/prefixes/",
                    },
                    {
                        children: "Security",
                        leftIcon: <SecurityIcon />,
                        to: "/extras/secrets/",
                    },
                    {
                        children: "Automation",
                        leftIcon: <AutomationIcon />,
                        to: "/extras/jobs/",
                    },
                    {
                        children: "Platform",
                        leftIcon: <PlatformIcon />,
                        to: "/extras/relationships/",
                    },
                ].map(({ children, to, ...rest }) => (
                    <ReactRouterNavLink key={to} to={to}>
                        {({ isActive }) => (
                            <NavbarSection
                                as="button"
                                isActive={
                                    isActive || children === currentContext
                                }
                                children={children}
                                {...rest}
                            />
                        )}
                    </ReactRouterNavLink>
                ))}
            </NavbarSections>

            <InputGroup flex="1" size="lg" variant="navbar">
                <InputLeftElement>
                    <SearchIcon />
                </InputLeftElement>
                <Input placeholder="Search..." />
            </InputGroup>
            {!isLoggedIn && <RouterButton to="/login/">Log In</RouterButton>}
            {isLoggedIn && (
                <Menu>
                    <MenuButton as={NavbarMenuButton} isDisabled={!isLoggedIn}>
                        {currentUser?.display || currentUser?.username}
                    </MenuButton>
                    <MenuList>
                        {[
                            {
                                children: "Log Out",
                                color: "red-1",
                                to: "/logout",
                            },
                        ].map(({ to, ...rest }) => (
                            <MenuItem
                                key={to}
                                as={ReactRouterLink}
                                to={to}
                                {...rest}
                            />
                        ))}
                    </MenuList>
                </Menu>
            )}
        </UINavbar>
    );
}
export default Navbar;
