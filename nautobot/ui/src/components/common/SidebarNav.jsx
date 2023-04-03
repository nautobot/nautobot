import {
    Accordion,
    AccordionButton,
    AccordionItem,
    AccordionPanel,
    Heading,
    SidebarButton,
} from "@nautobot/nautobot-ui";
import RouterLink from "@components/common/RouterLink";

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
            {menuInfo.map((item, idx) => (
                <AccordionItem key={idx}>
                    <Heading>
                        <AccordionButton isLast>{item.name}</AccordionButton>
                    </Heading>

                    <AccordionPanel>
                        {Object.entries(item.properties.groups).map(
                            (group, group_idx) => (
                                <Accordion
                                    allowMultiple
                                    variant="sidebarLevel1"
                                    key={group_idx}
                                >
                                    <AccordionItem>
                                        <Heading>
                                            <AccordionButton isLast>
                                                {group[0]}
                                            </AccordionButton>
                                        </Heading>
                                        <AccordionPanel>
                                            {Object.entries(group[1].items).map(
                                                (menu, menu_idx) => (
                                                    <SidebarButton
                                                        key={menu_idx}
                                                        level={2}
                                                    >
                                                        <RouterLink
                                                            to={menu[0]}
                                                        >
                                                            {menu[1].name}
                                                        </RouterLink>
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
