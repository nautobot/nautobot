import {
    Accordion,
    AccordionButton,
    AccordionItem,
    AccordionPanel,
    AccordionIcon,
    Heading,
    SidebarButton,
} from "@nautobot/nautobot-ui";
import { Link as ReactRouterLink } from "react-router-dom";

import { useGetUIMenuQuery } from "@utils/api";

// The sidebar accordion
export default function SidebarNav() {
    // Grab the UI menu from the RTK Query API
    const {
        data: menuInfo,
        isSuccess: isMenuSuccess,
        isError: isMenuError,
    } = useGetUIMenuQuery();

    if (isMenuError) return <div>Failed to load menu</div>;
    if (!isMenuSuccess) return <span>Loading...</span>;

    return (
        <Accordion allowMultiple variant="sidebarLevel0">
            {menuInfo.map((item, idx, arr) => (
                <AccordionItem key={item.name}>
                    <Heading>
                        <AccordionButton isLast={idx === arr.length - 1}>
                            {item.name}
                            <AccordionIcon />
                        </AccordionButton>
                    </Heading>
                    <AccordionPanel>
                        {Object.entries(item.properties.groups).map(
                            (group, group_idx, group_arr) => (
                                <Accordion
                                    allowMultiple
                                    variant="sidebarLevel1"
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
                                            {Object.entries(group[1].items).map(
                                                (menu, menu_idx, menu_arr) => (
                                                    <SidebarButton
                                                        as={ReactRouterLink}
                                                        key={menu_idx}
                                                        level={2}
                                                        to={menu[0]}
                                                        isLast={
                                                            menu_idx ===
                                                            menu_arr.length - 1
                                                        }
                                                    >
                                                        {menu[1].name}
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
            ))}
        </Accordion>
    );
}
