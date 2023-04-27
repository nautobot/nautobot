import {
    AutomationIcon,
    DcimIcon,
    IpamIcon,
    NautobotGrid,
    NautobotGridItem,
    PlatformIcon,
    SecurityIcon,
    Table,
    TableContainer,
    Tab,
    Tabs,
    TabList,
    TabPanel,
    TabPanels,
    Tag,
    TagLabel,
    Tbody,
    Td,
    Th,
    Thead,
    Tr,
} from "@nautobot/nautobot-ui";
import GenericView from "@views/generic/GenericView";
import HomePanel from "@components/HomePanel";

export default function Home() {
    return (
        <GenericView>
            <NautobotGrid background="white-0" columns="1 1 1 1 3 1">
                <HomePanel
                    icon=<DcimIcon />
                    title="Inventory"
                    data={{
                        Racks: 275,
                        "Device Types": 9,
                        Devices: 9,
                        "Virtual Chassis": 0,
                        "Device Redundancy Groups": 0,
                        Connections: 2618,
                    }}
                />
                <HomePanel
                    icon=<IpamIcon />
                    title="Networks"
                    data={{
                        VRFs: 2,
                        Prefixes: 1470,
                        "IP Addresses": 2426,
                        VLANs: 536,
                    }}
                />
                <HomePanel
                    icon=<SecurityIcon />
                    title="Security"
                    data={{
                        "Menu Item 1": 0,
                        "Menu Item 2": 0,
                        "Menu Item 3": 0,
                        "Menu Item 4": 0,
                        "Menu Item 5": 0,
                        "Menu Item 6": 0,
                    }}
                />
                <HomePanel
                    icon=<PlatformIcon />
                    title="Platform"
                    data={{
                        "Installed Apps/Plugins": 0,
                        "Git Repositories": 0,
                        Tags: 0,
                        Statuses: 0,
                        Roles: 0,
                        Relationships: 0,
                        "Computed Fields": 0,
                        "Custom Fields": 0,
                        "Custom Links": 0,
                    }}
                />
                <NautobotGridItem colSpan="3">
                    <TableContainer>
                        <Table>
                            <Thead>
                                <Tr _hover={{}}>
                                    <Th width="3em">
                                        <AutomationIcon />
                                    </Th>
                                    <Th>Automation</Th>
                                </Tr>
                            </Thead>
                            <Tbody>
                                <Tr>
                                    <Td colspan={2}>
                                        <Tabs variant="outline">
                                            <TabList>
                                                <Tab>
                                                    Job History{" "}
                                                    <Tag
                                                        size="sm"
                                                        variant="info"
                                                    >
                                                        <TagLabel>5</TagLabel>
                                                    </Tag>
                                                </Tab>
                                                <Tab>
                                                    Schedule{" "}
                                                    <Tag
                                                        size="sm"
                                                        variant="info"
                                                    >
                                                        <TagLabel>7</TagLabel>
                                                    </Tag>
                                                </Tab>
                                                <Tab>
                                                    Approvals{" "}
                                                    <Tag
                                                        size="sm"
                                                        variant="info"
                                                    >
                                                        <TagLabel>3</TagLabel>
                                                    </Tag>
                                                </Tab>
                                            </TabList>
                                            <TabPanels>
                                                <TabPanel></TabPanel>
                                                <TabPanel></TabPanel>
                                                <TabPanel></TabPanel>
                                            </TabPanels>
                                        </Tabs>
                                    </Td>
                                </Tr>
                            </Tbody>
                        </Table>
                    </TableContainer>
                </NautobotGridItem>
                <TableContainer>
                    <Table>
                        <Thead>
                            <Tr _hover={{}}>
                                <Th>Change Log</Th>
                            </Tr>
                        </Thead>
                        <Tbody>
                            <Tr></Tr>
                        </Tbody>
                    </Table>
                </TableContainer>
            </NautobotGrid>
        </GenericView>
    );
}
