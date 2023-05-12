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
import {
    Link as ReactRouterLink,
    NavLink as ReactRouterNavLink,
} from "react-router-dom";
import RouterButton from "@components/RouterButton";

export function Navbar({ appState }) {
    const isLoggedIn = appState.logged_in;

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
                                    isActive ||
                                    children === appState.currentContext
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
                        {appState.user?.display ||
                            [
                                ...(appState.user?.firstName
                                    ? [appState.user?.firstName]
                                    : []),
                                ...(appState.user?.lastName
                                    ? [appState.user?.lastName]
                                    : []),
                            ].join(" ") ||
                            appState.user?.username}
                    </MenuButton>
                    <MenuList>
                        {[
                            {
                                children: "Profile",
                                to: "/user/profile",
                            },
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
