import {
    Breadcrumb,
    Breadcrumbs,
    calc,
    Flex,
    getCssVar,
    NautobotGrid,
} from "@nautobot/nautobot-ui";
import { FiltersPanelContainer } from "@components/FiltersPanel";
import { Navbar } from "@components/Navbar";
import { useMemo } from "react";
import { useSelector } from "react-redux";
import {
    Link as ReactRouterLink,
    useLocation,
    useParams,
} from "react-router-dom";

import { useGetUIMenuQuery } from "@utils/api";
import { uiUrl } from "@utils/url";

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
                          children: objectData.display,
                          key: `${depth + 1}_${objectData.id}`,
                          to: uiUrl(objectData.url),
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
    gridBackground,
}) {
    const BREADCRUMB_KEY_HOME = "0_home";

    const { pathname } = useLocation();
    const { app_label, model_name, object_id } = useParams();

    const { data: menu, isSuccess } = useGetUIMenuQuery();

    // Using useMemo to prevent unnecessary re-execution of findMenuPathRecursive
    const menuPath = useMemo(
        () => findMenuPathRecursive(pathname, menu),
        [menu, pathname]
    );
    const breadcrumbs = useMemo(
        () =>
            (function () {
                if (pathname === "/" || !isSuccess || !menu) {
                    return [
                        {
                            key: BREADCRUMB_KEY_HOME,
                            type: "text",
                        },
                    ];
                }
                return breadcrumbsRecursive(menuPath, menu, objectData);
            })(),
        [menu, objectData, pathname, isSuccess, menuPath]
    );

    const currentState = useSelector((state) => state.appState);

    const hasBreadcrumbs =
        breadcrumbs.length > 0 && breadcrumbs[0].key !== BREADCRUMB_KEY_HOME;

    const isListView = Boolean(app_label && model_name && !object_id);

    return (
        <Flex
            background="gray-0"
            direction="column"
            gap="md"
            height="full"
            paddingTop="md"
            width="full"
        >
            <Navbar appState={currentState} />

            <Flex flex="1" overflow="hidden">
                <Flex
                    direction="column"
                    flex="1"
                    overflow="auto"
                    paddingBottom="md"
                    paddingX="md"
                >
                    {hasBreadcrumbs ? (
                        <Breadcrumbs
                            flex="none"
                            marginBottom="md"
                            position="relative"
                            zIndex="5"
                        >
                            {breadcrumbs.map((props) => (
                                <Breadcrumb {...props} />
                            ))}
                        </Breadcrumbs>
                    ) : null}

                    <NautobotGrid
                        alignItems="start"
                        columns={columns}
                        rows={rows}
                        background={gridBackground}
                        gridAutoRows="auto"
                        {...(hasBreadcrumbs
                            ? { minHeight: "auto" }
                            : { flex: "1 0 auto" })}
                        {...(isListView
                            ? {
                                  gridAutoRows:
                                      getCssVar("sizes.full").reference,
                                  maxHeight: calc.subtract(
                                      getCssVar("sizes.full"),
                                      getCssVar("lineHeights.normal"),
                                      getCssVar("space.md")
                                  ),
                              }
                            : undefined)}
                    >
                        {typeof children === "function"
                            ? children(menuPath)
                            : children}
                    </NautobotGrid>
                </Flex>

                <FiltersPanelContainer />
            </Flex>
        </Flex>
    );
}
