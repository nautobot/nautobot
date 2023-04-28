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
                for (const context in menu.data) {
                    for (const group in menu.data[context].groups) {
                        for (const urlPatternOrSubgroup in menu.data[context]
                            .groups[group].items) {
                            if (pathname.startsWith(urlPatternOrSubgroup)) {
                                // It's a urlPattern, no subGroup currently selected
                                return [
                                    // Selected context
                                    {
                                        children: context,
                                        key: `0_${context}`,
                                        type: "text",
                                    },
                                    // Selected group, with menu of all available groups in the context
                                    {
                                        children: group,
                                        items: Object.keys(
                                            menu.data[context].groups
                                        ).map((name) => ({
                                            as: ReactRouterLink,
                                            children: name,
                                            to: Object.entries(
                                                menu.data[context].groups[name]
                                                    .items
                                            )[0][0],
                                        })),
                                        key: `1_${group}`,
                                        type: "menu",
                                    },
                                    // Selected item within the group, with menu of peer items and/or subgroups
                                    {
                                        children:
                                            menu.data[context].groups[group]
                                                .items[urlPatternOrSubgroup]
                                                .name,
                                        items: Object.keys(
                                            menu.data[context].groups[group]
                                                .items
                                        ).map((name) => ({
                                            as: ReactRouterLink,
                                            children:
                                                menu.data[context].groups[group]
                                                    .items[name].name || name,
                                            to: menu.data[context].groups[group]
                                                .items[name].items
                                                ? Object.entries(
                                                      menu.data[context].groups[
                                                          group
                                                      ].items[name].items ?? {}
                                                  )[0][0]
                                                : name,
                                        })),
                                        key: `2_${menu.data[context].groups[group].items[urlPatternOrSubgroup].name}`,
                                        type: "menu",
                                    },
                                    // Selected object instance
                                    ...(objectData
                                        ? [
                                              {
                                                  as: ReactRouterLink,
                                                  children: objectData.name,
                                                  key: `3_${objectData.id}`,
                                                  to: `${urlPatternOrSubgroup}${objectData.id}`,
                                                  type: "link",
                                              },
                                          ]
                                        : []),
                                ];
                            }
                            // It might also be a sub-group with its own nested items
                            for (const urlPattern in menu.data[context].groups[
                                group
                            ].items[urlPatternOrSubgroup].items) {
                                if (pathname.startsWith(urlPattern)) {
                                    return [
                                        // Selected context
                                        {
                                            children: context,
                                            key: `0_${context}`,
                                            type: "text",
                                        },
                                        // Selected group, with menu of all available groups in the context
                                        {
                                            children: group,
                                            items: Object.keys(
                                                menu.data[context].groups
                                            ).map((name) => ({
                                                as: ReactRouterLink,
                                                children: name,
                                                to: Object.entries(
                                                    menu.data[context].groups[
                                                        name
                                                    ].items
                                                )[0][0],
                                            })),
                                            key: `1_${group}`,
                                            type: "menu",
                                        },
                                        // Selected subgroup within the group, with menu of peer items and/or subgroups
                                        {
                                            children: urlPatternOrSubgroup,
                                            items: Object.keys(
                                                menu.data[context].groups[group]
                                                    .items
                                            ).map((name) => ({
                                                as: ReactRouterLink,
                                                children:
                                                    menu.data[context].groups[
                                                        group
                                                    ].items[name].name || name,
                                                to: menu.data[context].groups[
                                                    group
                                                ].items[name].items
                                                    ? Object.entries(
                                                          menu.data[context]
                                                              .groups[group]
                                                              .items[name]
                                                              .items ?? {}
                                                      )[0][0]
                                                    : name,
                                            })),
                                            key: `2_${urlPatternOrSubgroup}`,
                                            type: "menu",
                                        },
                                        // Selected item within the subgroup, with menu of peer items
                                        {
                                            children:
                                                menu.data[context].groups[group]
                                                    .items[urlPatternOrSubgroup]
                                                    .items[urlPattern].name,
                                            items: Object.entries(
                                                menu.data[context].groups[group]
                                                    .items[urlPatternOrSubgroup]
                                                    .items
                                            ).map(([to, { name }]) => ({
                                                as: ReactRouterLink,
                                                children: name,
                                                to,
                                            })),
                                            key: `3_${menu.data[context].groups[group].items[urlPatternOrSubgroup].items[urlPattern].name}`,
                                            type: "menu",
                                        },
                                        // Selected object instance
                                        ...(objectData
                                            ? [
                                                  {
                                                      as: ReactRouterLink,
                                                      children: objectData.name,
                                                      key: `3_${objectData.id}`,
                                                      to: `${urlPatternOrSubgroup}${objectData.id}`,
                                                      type: "link",
                                                  },
                                              ]
                                            : []),
                                    ];
                                }
                            }
                        }
                    }
                }
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
                >
                    {children}
                </NautobotGrid>
            </Box>
        </Flex>
    );
}
