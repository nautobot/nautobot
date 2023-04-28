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

export function Navbar({ session, currentContext }) {
    const isLoggedIn = !!session?.logged_in;

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
                        to: "/security",
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
                        {session?.user?.display ||
                            [
                                ...(session?.user?.firstName
                                    ? [session?.user?.firstName]
                                    : []),
                                ...(session?.user?.lastName
                                    ? [session?.user?.lastName]
                                    : []),
                            ].join(" ") ||
                            session?.user?.username}
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
