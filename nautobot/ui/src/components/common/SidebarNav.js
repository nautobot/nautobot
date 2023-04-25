import {
    Accordion,
    AccordionButton,
    AccordionItem,
    AccordionPanel,
    AccordionIcon,
    AutomationIcon,
    DcimIcon,
    Heading,
    IpamIcon,
    PlatformIcon,
    SecurityIcon,
    SidebarButton,
} from "@nautobot/nautobot-ui";
import { Link as ReactRouterLink } from "react-router-dom";
import { useSelector } from "react-redux";

import { useGetUIMenuQuery } from "@utils/api";

// The sidebar accordion
export default function SidebarNav() {
    // Grab the UI menu from the RTK Query API
    const {
        data: menuInfo,
        isSuccess: isMenuSuccess,
        isError: isMenuError,
    } = useGetUIMenuQuery();
    const appContext = useSelector((state) => state.appContext);
    const appContextToIcon = {
        Inventory: DcimIcon,
        Networks: IpamIcon,
        Security: SecurityIcon,
        Automation: AutomationIcon,
        Platform: PlatformIcon,
    };

    if (appContext === "") {
        return <></>;
    }
    const Icon = appContextToIcon[appContext];

    if (!isMenuSuccess || isMenuError) {
        return <></>;
    }

    return (
        <>
            <Heading variant="sidebar">
                <Icon />
                {appContext}
            </Heading>
            <Accordion allowMultiple variant="sidebarLevel0">
                {Object.entries(menuInfo[appContext].groups).map(
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
                                            group_idx === group_arr.length - 1
                                        }
                                    >
                                        {group[0]}
                                        <AccordionIcon />
                                    </AccordionButton>
                                </Heading>
                                <AccordionPanel>
                                    {Object.entries(group[1].items).map(
                                        (menu, menu_idx, menu_arr) =>
                                            menu[0][0] == "/" ? (
                                                <SidebarButton
                                                    as={ReactRouterLink}
                                                    key={menu_idx}
                                                    level={1}
                                                    to={menu[0]}
                                                    isLast={
                                                        menu_idx ===
                                                        menu_arr.length - 1
                                                    }
                                                >
                                                    {menu[1].name}
                                                </SidebarButton>
                                            ) : (
                                                <Accordion
                                                    allowMultiple
                                                    variant="sidebarLevel1"
                                                    key={menu_idx}
                                                >
                                                    <Heading>
                                                        <AccordionButton
                                                            isLast={
                                                                menu_idx ===
                                                                menu_arr.length -
                                                                    1
                                                            }
                                                        >
                                                            {menu[0]}
                                                            <AccordionIcon />
                                                        </AccordionButton>
                                                    </Heading>
                                                    <AccordionPanel>
                                                        {Object.entries(
                                                            menu[1].items
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
                                                                    level={2}
                                                                    to={
                                                                        submenu[0]
                                                                    }
                                                                    isLast={
                                                                        submenu_idx ===
                                                                        submenu_arr.length -
                                                                            1
                                                                    }
                                                                >
                                                                    {
                                                                        submenu[1]
                                                                            .name
                                                                    }
                                                                </SidebarButton>
                                                            )
                                                        )}
                                                    </AccordionPanel>
                                                </Accordion>
                                            )
                                    )}
                                </AccordionPanel>
                            </AccordionItem>
                        </Accordion>
                    )
                )}
            </Accordion>
        </>
    );
}
