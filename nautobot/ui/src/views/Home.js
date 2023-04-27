import {
    AutomationIcon,
    DcimIcon,
    HistoryIcon,
    IpamIcon,
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
import JobHistoryTable from "@components/JobHistoryTable";

export default function Home() {
    return (
        <GenericView columns="1 1 1 1 3 1" gridBackground="white-0">
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
                            <Tr _hover={{}}>
                                <Td colspan={2}>
                                    <Tabs variant="outline">
                                        <TabList>
                                            <Tab>
                                                Job History{" "}
                                                <Tag size="sm" variant="info">
                                                    <TagLabel>5</TagLabel>
                                                </Tag>
                                            </Tab>
                                            <Tab>
                                                Schedule{" "}
                                                <Tag size="sm" variant="info">
                                                    <TagLabel>7</TagLabel>
                                                </Tag>
                                            </Tab>
                                            <Tab>
                                                Approvals{" "}
                                                <Tag size="sm" variant="info">
                                                    <TagLabel>3</TagLabel>
                                                </Tag>
                                            </Tab>
                                        </TabList>
                                        <TabPanels>
                                            <TabPanel>
                                                <JobHistoryTable
                                                    rows={[
                                                        {
                                                            user: "John Smith",
                                                            completed:
                                                                "2022-12-19 10:31",
                                                            job: "Generate Vulnerabilities / We can also put more details here since it's longer / We can also put more details here since it's longer / We can also put more details here since it's longer.",
                                                        },
                                                        {
                                                            user: "John Smith",
                                                            completed:
                                                                "2022-12-18 10:31",
                                                            job: "Generate Vulnerabilities",
                                                        },
                                                        {
                                                            user: "John Smith",
                                                            completed:
                                                                "2022-12-17 10:31",
                                                            job: "Generate Vulnerabilities",
                                                        },
                                                        {
                                                            user: "John Smith",
                                                            completed:
                                                                "2022-12-16 10:31",
                                                            job: "Generate Vulnerabilities",
                                                        },
                                                        {
                                                            user: "John Smith",
                                                            completed:
                                                                "2022-12-15 10:31",
                                                            job: "Generate Vulnerabilities",
                                                        },
                                                    ]}
                                                />
                                            </TabPanel>
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
            <NautobotGridItem>
                <TableContainer>
                    <Table>
                        <Thead>
                            <Tr _hover={{}}>
                                <Th width="3em">
                                    <HistoryIcon />
                                </Th>
                                <Th colspan={4}>Change Log</Th>
                            </Tr>
                        </Thead>
                        <Tbody>
                            <Tr>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>John Smith</Td>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>2022-12-19 10:31</Td>
                                <Td style={{ "text-align": "right" }}>
                                    <Tag variant="success">
                                        <TagLabel>Success</TagLabel>
                                    </Tag>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td colspan={5}>
                                    job - Generate Vulnerabilities
                                </Td>
                            </Tr>
                            <Tr>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>John Smith</Td>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>2022-12-19 10:31</Td>
                                <Td style={{ "text-align": "right" }}>
                                    <Tag variant="success">
                                        <TagLabel>Success</TagLabel>
                                    </Tag>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td colspan={5}>
                                    job - Generate Vulnerabilities
                                </Td>
                            </Tr>
                            <Tr>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>John Smith</Td>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>2022-12-19 10:31</Td>
                                <Td style={{ "text-align": "right" }}>
                                    <Tag variant="critical">
                                        <TagLabel>Error</TagLabel>
                                    </Tag>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td colspan={5}>
                                    job - Generate Vulnerabilities
                                </Td>
                            </Tr>
                            <Tr>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>John Smith</Td>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>2022-12-19 10:31</Td>
                                <Td style={{ "text-align": "right" }}>
                                    <Tag variant="success">
                                        <TagLabel>Success</TagLabel>
                                    </Tag>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td colspan={5}>
                                    job - Generate Vulnerabilities
                                </Td>
                            </Tr>
                            <Tr>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>John Smith</Td>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>2022-12-19 10:31</Td>
                                <Td style={{ "text-align": "right" }}>
                                    <Tag variant="success">
                                        <TagLabel>Success</TagLabel>
                                    </Tag>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td colspan={5}>
                                    job - Generate Vulnerabilities
                                </Td>
                            </Tr>
                            <Tr>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>John Smith</Td>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>2022-12-19 10:31</Td>
                                <Td style={{ "text-align": "right" }}>
                                    <Tag variant="success">
                                        <TagLabel>Success</TagLabel>
                                    </Tag>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td colspan={5}>
                                    job - Generate Vulnerabilities
                                </Td>
                            </Tr>
                        </Tbody>
                    </Table>
                </TableContainer>
            </NautobotGridItem>
        </GenericView>
    );
}
