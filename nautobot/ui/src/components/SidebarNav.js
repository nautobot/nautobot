import {
    Accordion,
    AccordionButton,
    AccordionItem,
    AccordionPanel,
    AccordionIcon,
    Heading,
    SidebarButton,
} from "@nautobot/nautobot-ui";
import { Link as ReactRouterLink, useLocation } from "react-router-dom";
import { useSelector } from "react-redux";
import {
    isLoggedInSelector,
    getCurrentContextSelector,
    getMenuInfoSelector,
} from "@utils/store";
import { appContextIcons } from "@constants/icons";

import { isEnabledRoute } from "@utils/navigation";

// The sidebar accordion
export default function SidebarNav() {
    const isLoggedIn = useSelector(isLoggedInSelector);
    const currentContext = useSelector(getCurrentContextSelector);
    const menuInfo = useSelector(getMenuInfoSelector);
    const location = useLocation();

    let CurrentContextIcon = <></>;

    if (currentContext) {
        CurrentContextIcon = appContextIcons[currentContext];
    }

    const isDisabledLinkProps = (route) => {
        if (!isEnabledRoute(route)) {
            return {
                color: "gray.500",
                cursor: "not-allowed",
                _hover: {
                    color: "gray.500",
                },
                // Prevent link click event
                onClick: (e) => e.preventDefault(),
            };
        }
        return {};
    };

    return (
        <>
            <Heading variant="sidebar">
                <CurrentContextIcon />
                {currentContext}
            </Heading>
            {isLoggedIn &&
                menuInfo !== {} &&
                menuInfo[currentContext] !== undefined && (
                    <Accordion allowMultiple variant="sidebarLevel0">
                        {Object.entries(menuInfo[currentContext]).map(
                            (group, group_idx, group_arr) => (
                                <Accordion
                                    allowMultiple
                                    variant="sidebarLevel0"
                                    key={group[0]}
                                >
                                    <AccordionItem>
                                        <Heading>
                                            <AccordionButton
                                                isLast={
                                                    group_idx ===
                                                    group_arr.length - 1
                                                }
                                            >
                                                {group[0]}
                                                <AccordionIcon />
                                            </AccordionButton>
                                        </Heading>
                                        <AccordionPanel>
                                            {Object.entries(group[1]).map(
                                                (menu, menu_idx, menu_arr) =>
                                                    typeof menu[1] ===
                                                    "string" ? (
                                                        <SidebarButton
                                                            as={ReactRouterLink}
                                                            key={menu_idx}
                                                            level={1}
                                                            to={menu[1]}
                                                            isLast={
                                                                menu_idx ===
                                                                menu_arr.length -
                                                                    1
                                                            }
                                                            active={
                                                                menu[1] ===
                                                                location.pathname
                                                            }
                                                            {...isDisabledLinkProps(
                                                                menu[1]
                                                            )}
                                                        >
                                                            {menu[0]}
                                                        </SidebarButton>
                                                    ) : (
                                                        <Accordion
                                                            allowMultiple
                                                            variant="sidebarLevel1"
                                                            key={menu_idx}
                                                        >
                                                            <AccordionItem>
                                                                <Heading>
                                                                    <AccordionButton
                                                                        isLast={
                                                                            menu_idx ===
                                                                            menu_arr.length -
                                                                                1
                                                                        }
                                                                    >
                                                                        {
                                                                            menu[0]
                                                                        }
                                                                        <AccordionIcon />
                                                                    </AccordionButton>
                                                                </Heading>
                                                                <AccordionPanel>
                                                                    {Object.entries(
                                                                        menu[1]
                                                                    ).map(
                                                                        (
                                                                            submenu,
                                                                            submenu_idx,
                                                                            submenu_arr
                                                                        ) => (
                                                                            <SidebarButton
                                                                                as={
                                                                                    ReactRouterLink
                                                                                }
                                                                                key={
                                                                                    submenu_idx
                                                                                }
                                                                                level={
                                                                                    2
                                                                                }
                                                                                to={
                                                                                    submenu[1]
                                                                                }
                                                                                isLast={
                                                                                    submenu_idx ===
                                                                                    submenu_arr.length -
                                                                                        1
                                                                                }
                                                                                active={
                                                                                    submenu[1] ===
                                                                                    location.pathname
                                                                                }
                                                                                {...isDisabledLinkProps(
                                                                                    submenu[1]
                                                                                )}
                                                                            >
                                                                                {
                                                                                    submenu[0]
                                                                                }
                                                                            </SidebarButton>
                                                                        )
                                                                    )}
                                                                </AccordionPanel>
                                                            </AccordionItem>
                                                        </Accordion>
                                                    )
                                            )}
                                        </AccordionPanel>
                                    </AccordionItem>
                                </Accordion>
                            )
                        )}
                    </Accordion>
                )}
        </>
    );
}
