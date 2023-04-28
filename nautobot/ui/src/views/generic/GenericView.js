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
                    for (const group in menu.data[context]) {
                        for (const subgroup_or_item in menu.data[context][
                            group
                        ]) {
                            if (
                                typeof menu.data[context][group][
                                    subgroup_or_item
                                ] === "string" &&
                                pathname.startsWith(
                                    menu.data[context][group][subgroup_or_item]
                                )
                            ) {
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
                                            menu.data[context]
                                        ).map((group_name) => ({
                                            as: ReactRouterLink,
                                            children: group_name,
                                            // Link to the first sub-item in that group
                                            to: Object.entries(
                                                menu.data[context][group_name]
                                            )[0][1],
                                        })),
                                        key: `1_${group}`,
                                        type: "menu",
                                    },
                                    // Selected item within the group, with menu of peer items and/or subgroups
                                    {
                                        children: subgroup_or_item,
                                        items: Object.keys(
                                            menu.data[context][group]
                                        ).map((subgroup_or_item_name) => ({
                                            as: ReactRouterLink,
                                            children: subgroup_or_item_name,
                                            to:
                                                typeof menu.data[context][
                                                    group
                                                ][subgroup_or_item_name] ==
                                                "object"
                                                    ? Object.entries(
                                                          menu.data[context][
                                                              group
                                                          ][
                                                              subgroup_or_item_name
                                                          ] ?? {}
                                                      )[0][1]
                                                    : menu.data[context][group][
                                                          subgroup_or_item_name
                                                      ],
                                        })),
                                        key: `2_${subgroup_or_item}`,
                                        type: "menu",
                                    },
                                    // Selected object instance
                                    ...(objectData
                                        ? [
                                              {
                                                  as: ReactRouterLink,
                                                  children: objectData.name,
                                                  key: `3_${objectData.id}`,
                                                  to: `${menu.data[context][group][subgroup_or_item]}${objectData.id}`,
                                                  type: "link",
                                              },
                                          ]
                                        : []),
                                ];
                            }
                            if (
                                typeof menu.data[context][group][
                                    subgroup_or_item
                                ] === "object"
                            ) {
                                // It is a sub-group with its own nested items
                                for (const subitem in menu.data[context][group][
                                    subgroup_or_item
                                ]) {
                                    if (
                                        pathname.startsWith(
                                            menu.data[context][group][
                                                subgroup_or_item
                                            ][subitem]
                                        )
                                    ) {
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
                                                    menu.data[context]
                                                ).map((group_name) => ({
                                                    as: ReactRouterLink,
                                                    children: group_name,
                                                    to: Object.entries(
                                                        menu.data[context][
                                                            group_name
                                                        ]
                                                    )[0][0],
                                                })),
                                                key: `1_${group}`,
                                                type: "menu",
                                            },
                                            // Selected subgroup within the group, with menu of peer items and/or subgroups
                                            {
                                                children: subgroup_or_item,
                                                items: Object.keys(
                                                    menu.data[context][group]
                                                ).map((subgroup_name) => ({
                                                    as: ReactRouterLink,
                                                    children: subgroup_name,
                                                    to: Object.entries(
                                                        menu.data[context][
                                                            group
                                                        ][subgroup_name]
                                                    )[0][0],
                                                })),
                                                key: `2_${subgroup_or_item}`,
                                                type: "menu",
                                            },
                                            // Selected item within the subgroup, with menu of peer items
                                            {
                                                children: subitem,
                                                items: Object.keys(
                                                    menu.data[context][group][
                                                        subgroup_or_item
                                                    ]
                                                ).map((subitem_name) => ({
                                                    as: ReactRouterLink,
                                                    children: subitem_name,
                                                    to: Object.entries(
                                                        menu.data[context][
                                                            group
                                                        ][subgroup_or_item][
                                                            subitem_name
                                                        ]
                                                    )[0][0],
                                                })),
                                                key: `3_${subitem}`,
                                                type: "menu",
                                            },
                                            // Selected object instance
                                            ...(objectData
                                                ? [
                                                      {
                                                          as: ReactRouterLink,
                                                          children:
                                                              objectData.name,
                                                          key: `4_${objectData.id}`,
                                                          to: `${menu.data[context][group][subgroup_or_item][subitem]}${objectData.id}`,
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
