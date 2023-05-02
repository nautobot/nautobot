import {
    Box,
    Breadcrumb,
    Breadcrumbs,
    Flex,
    NautobotGrid,
} from "@nautobot/nautobot-ui";
import { Navbar } from "@components/Navbar";
import { useMemo } from "react";
import { useSelector } from "react-redux";
import { Link as ReactRouterLink, useLocation } from "react-router-dom";

import { useGetSessionQuery, useGetUIMenuQuery } from "@utils/api";

// Descend into the menu "data" until we find a leaf whose URL matches "pathname", and return the keys to get there
function findMenuPathRecursive(pathname, data) {
    for (const key in data) {
        if (typeof data[key] == "string") {
            if (pathname.startsWith(data[key])) {
                return [key];
            }
        } else {
            let pathToLeaf = findMenuPathRecursive(pathname, data[key]);
            if (pathToLeaf !== null) {
                return [key].concat(pathToLeaf);
            }
        }
    }
    return null;
}

// Descend into the menu "data" until we find the first leaf and return its URL.
function firstLinkInMenu(data) {
    return typeof data === "string"
        ? data
        : firstLinkInMenu(Object.values(data)[0] ?? "");
}

// Descend into the menu "data" along the given path and construct breadcrumbs/menus corresponding to that path
function breadcrumbsRecursive(pathToLeaf, data, objectData, depth = 0) {
    let key = pathToLeaf[0];
    let entry = {
        children: key,
        items: Object.keys(data).map((peer_name) => ({
            as: ReactRouterLink,
            children: peer_name,
            to: firstLinkInMenu(data[peer_name]),
        })),
        key: `${depth}_${key}`,
        type: "menu",
    };
    if (pathToLeaf.length === 1) {
        // Selected leaf within the menu, plus (below) possibly a specific object instance
        return [
            entry,
            ...(objectData
                ? [
                      {
                          as: ReactRouterLink,
                          children: objectData.name,
                          key: `${depth + 1}_${objectData.id}`,
                          to: `${data[key]}${objectData.id}`,
                          type: "link",
                      },
                  ]
                : []),
        ];
    }
    return [entry].concat(
        breadcrumbsRecursive(
            pathToLeaf.slice(1),
            data[key],
            objectData,
            depth + 1
        )
    );
}

export default function GenericView({
    children,
    columns = "4",
    objectData,
    rows,
    gridBackground = "",
}) {
    const { pathname } = useLocation();
    const menu = useGetUIMenuQuery();
    const session = useGetSessionQuery();

    const breadcrumbs = useMemo(
        () =>
            (function () {
                if (pathname === "/") {
                    return [
                        {
                            children: "Home",
                            key: `0_home`,
                            type: "text",
                        },
                    ];
                }
                return breadcrumbsRecursive(
                    findMenuPathRecursive(pathname, menu.data),
                    menu.data,
                    objectData
                );
            })(),
        [menu, objectData, pathname]
    );

    const currentContext = useSelector(
        (state) => state.appState.currentContext
    );

    return (
        <Flex
            direction="column"
            background="gray-0"
            gap="md"
            height="full"
            paddingTop="md"
            width="full"
        >
            <Navbar session={session?.data} currentContext={currentContext} />
            <Box flex="1" overflow="auto">
                <Breadcrumbs paddingX="md">
                    {breadcrumbs.map((props) => (
                        <Breadcrumb {...props} />
                    ))}
                </Breadcrumbs>

                <NautobotGrid
                    alignItems="start"
                    columns={columns}
                    rows={rows}
                    background={gridBackground}
                    gridAutoRows="auto"
                >
                    {children}
                </NautobotGrid>
            </Box>
        </Flex>
    );
}
