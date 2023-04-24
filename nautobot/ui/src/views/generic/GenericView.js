import {
    AutomationIcon,
    Box,
    Breadcrumb,
    Breadcrumbs,
    DcimIcon,
    Flex,
    Input,
    InputGroup,
    InputLeftElement,
    IpamIcon,
    Menu,
    MenuButton,
    MenuItem,
    MenuList,
    NautobotGrid,
    Navbar,
    NavbarMenuButton,
    NavbarSection,
    NavbarSections,
    PlatformIcon,
    SearchIcon,
    SecurityIcon,
} from "@nautobot/nautobot-ui";
import { useMemo } from "react";
import {
    Link as ReactRouterLink,
    NavLink as ReactRouterNavLink,
    useLocation,
} from "react-router-dom";

import { useGetSessionQuery, useGetUIMenuQuery } from "@utils/api";

export default function GenericView({
    children,
    columns = "4",
    objectData,
    rows,
}) {
    const { pathname } = useLocation();

    const menu = useGetUIMenuQuery();
    const session = useGetSessionQuery();

    const breadcrumbs = useMemo(
        () =>
            (menu?.data ?? []).reduce((breadcrumbs, root) => {
                // Use `for ... in` instead of array methods to simplify return.
                for (const group in root.properties.groups) {
                    const { items } = root.properties.groups[group];

                    for (const item in items) {
                        if (pathname.startsWith(item)) {
                            return [
                                {
                                    children: root.name,
                                    key: `0_${root.name}`,
                                    type: "text",
                                },
                                {
                                    children: group,
                                    items: Object.keys(
                                        root.properties.groups
                                    ).map((name) => ({
                                        as: ReactRouterLink,
                                        children: name,
                                        to: Object.entries(
                                            root.properties.groups[name].items
                                        ).sort(
                                            ([, a], [, b]) =>
                                                a.weight - b.weight
                                        )[0][0],
                                    })),
                                    key: `1_${group}`,
                                    type: "menu",
                                },
                                {
                                    children: items[item].name,
                                    items: Object.entries(items).map(
                                        ([to, { name }]) => ({
                                            as: ReactRouterLink,
                                            children: name,
                                            to,
                                        })
                                    ),
                                    key: `2_${items[item].name}`,
                                    type: "menu",
                                },
                                ...(objectData
                                    ? [
                                          {
                                              as: ReactRouterLink,
                                              children: objectData.name,
                                              key: `3_${objectData.id}`,
                                              to: `${item}${objectData.id}`,
                                              type: "link",
                                          },
                                      ]
                                    : []),
                            ];
                        }
                    }
                }

                return breadcrumbs;
            }, []),
        [menu, objectData, pathname]
    );

    const isLoggedIn = !!session?.data?.logged_in;

    return (
        <Flex
            direction="column"
            background="gray-0"
            gap="md"
            height="full"
            paddingTop="md"
            width="full"
        >
            <Navbar>
                <NavbarSections>
                    {[
                        {
                            children: "Inventory",
                            leftIcon: <DcimIcon />,
                            to: "/dcim",
                        },
                        {
                            children: "Networks",
                            leftIcon: <IpamIcon />,
                            to: "/ipam",
                        },
                        {
                            children: "Security",
                            leftIcon: <SecurityIcon />,
                            to: "/security",
                        },
                        {
                            children: "Automation",
                            leftIcon: <AutomationIcon />,
                            to: "/automation",
                        },
                        {
                            children: "Platform",
                            leftIcon: <PlatformIcon />,
                            to: "/platform",
                        },
                    ].map(({ to, ...rest }) => (
                        <ReactRouterNavLink key={to} to={to}>
                            {({ isActive }) => (
                                <NavbarSection
                                    as="span"
                                    isActive={isActive}
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

                <Menu>
                    <MenuButton as={NavbarMenuButton} isDisabled={!isLoggedIn}>
                        {session?.data?.user?.display ||
                            [
                                ...(session?.data?.user?.firstName
                                    ? [session?.data?.user?.firstName]
                                    : []),
                                ...(session?.data?.user?.lastName
                                    ? [session?.data?.user?.lastName]
                                    : []),
                            ].join(" ") ||
                            session?.data?.user?.username}
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
            </Navbar>

            <Box flex="1" overflow="auto">
                <Breadcrumbs paddingX="md">
                    {breadcrumbs.map((props) => (
                        <Breadcrumb {...props} />
                    ))}
                </Breadcrumbs>

                <NautobotGrid alignItems="start" columns={columns} rows={rows}>
                    {children}
                </NautobotGrid>
            </Box>
        </Flex>
    );
}
