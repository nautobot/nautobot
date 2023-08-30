import { useSelector } from "react-redux";
import {
    Link as ReactRouterLink,
    NavLink as ReactRouterNavLink,
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
import {
    currentUserSelector,
    isLoggedInSelector,
    getCurrentContextSelector,
    getMenuInfoSelector,
} from "@utils/store";
import { isEnabledContextRoute } from "@utils/navigation";

export function Navbar() {
    const isLoggedIn = useSelector(isLoggedInSelector);
    const currentContext = useSelector(getCurrentContextSelector);
    const currentUser = useSelector(currentUserSelector);
    const menuInfo = useSelector(getMenuInfoSelector);

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
                                disabled={
                                    !isEnabledContextRoute(menuInfo, [children])
                                }
                                _disabled={{
                                    color: "gray.400",
                                    cursor: "not-allowed",
                                }}
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
