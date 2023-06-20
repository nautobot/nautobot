import { useSelector } from "react-redux";
import {
    Link as ReactRouterLink,
    NavLink as ReactRouterNavLink,
    useMatch,
} from "react-router-dom";
import {
    AutomationIcon,
    DcimIcon,
    HomeIcon,
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
    isLoggedInSelector,
    getCurrentContextSelector,
    currentUserSelector,
} from "@utils/store";

export function Navbar() {
    const isLoggedIn = useSelector(isLoggedInSelector);
    const currentContext = useSelector(getCurrentContextSelector);
    const currentUser = useSelector(currentUserSelector);

    const isHomeActive =
        useMatch({
            path: "/",
            exact: true,
        }) !== null;

    return (
        <UINavbar>
            <ReactRouterNavLink exact to="/">
                <NavbarSection
                    children="Home"
                    leftIcon={<HomeIcon />}
                    isActive={isHomeActive}
                    as="span"
                    paddingRight={0}
                />
            </ReactRouterNavLink>

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
                        to: "/ipam/ip-addresses/",
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
                                as="span"
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
