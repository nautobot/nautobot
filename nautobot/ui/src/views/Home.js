import {
    Button,
    NautobotGrid,
    NautobotGridItem,
    Table,
    TableContainer,
    Tab,
    Tabs,
    TabList,
    TabPanel,
    TabPanels,
    Tbody,
    Td,
    Th,
    Thead,
    Tr,
} from "@nautobot/nautobot-ui";
import GenericView from "@views/generic/GenericView";

export default function Home() {
    return (
        <GenericView columns="1 1 1 1">
            <NautobotGrid background="white-0">
                <TableContainer>
                    <Table>
                        <Thead>
                            <Tr _hover={{}}>
                                <Th colspan={2}>Inventory</Th>
                            </Tr>
                        </Thead>
                        <Tbody>
                            <Tr>
                                <Td>Racks</Td>
                                <Td>
                                    <Button variant="primary">275</Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Device Types</Td>
                                <Td>
                                    <Button variant="primary">9</Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Devices</Td>
                                <Td>
                                    <Button variant="primary">9</Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Virtual Chassis</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Device Redundancy Groups</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Connections</Td>
                                <Td>
                                    <Button variant="primary">2618</Button>
                                </Td>
                            </Tr>
                        </Tbody>
                    </Table>
                </TableContainer>
                <TableContainer>
                    <Table>
                        <Thead>
                            <Tr _hover={{}}>
                                <Th colspan={2}>Networks</Th>
                            </Tr>
                        </Thead>
                        <Tbody>
                            <Tr>
                                <Td>VRFs</Td>
                                <Td>
                                    <Button variant="primary">2</Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Prefixes</Td>
                                <Td>
                                    <Button variant="primary">1470</Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>IP Addresses</Td>
                                <Td>
                                    <Button variant="primary">2426</Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>VLANs</Td>
                                <Td>
                                    <Button variant="primary">536</Button>
                                </Td>
                            </Tr>
                        </Tbody>
                    </Table>
                </TableContainer>
                <TableContainer>
                    <Table>
                        <Thead>
                            <Tr _hover={{}}>
                                <Th colspan={2}>Security</Th>
                            </Tr>
                        </Thead>
                        <Tbody>
                            <Tr>
                                <Td>Menu Item 1</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Menu Item 2</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Menu Item 3</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Menu Item 4</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Menu Item 5</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Menu Item 6</Td>
                                <Td>
                                    <Button variant="primary">0</Button>
                                </Td>
                            </Tr>
                        </Tbody>
                    </Table>
                </TableContainer>
                <TableContainer>
                    <Table>
                        <Thead>
                            <Tr _hover={{}}>
                                <Th colspan={2}>Platform</Th>
                            </Tr>
                        </Thead>
                        <Tbody>
                            <Tr>
                                <Td>Installed Apps/Plugins</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Git Repositories</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Tags</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Statuses</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Roles</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Relationships</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Computed Fields</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Custom Fields</Td>
                                <Td>
                                    <Button variant="primary" isDisabled={true}>
                                        0
                                    </Button>
                                </Td>
                            </Tr>
                            <Tr>
                                <Td>Custom Links</Td>
                                <Td>
                                    <Button variant="primary">3</Button>
                                </Td>
                            </Tr>
                        </Tbody>
                    </Table>
                </TableContainer>
                <NautobotGridItem colSpan="3">
                    <TableContainer>
                        <Table>
                            <Thead>
                                <Tr _hover={{}}>
                                    <Th>Automation</Th>
                                </Tr>
                            </Thead>
                            <Tbody>
                                <Tr>
                                    <Td>
                                        <Tabs variant="outline">
                                            <TabList>
                                                <Tab>
                                                    Job History{" "}
                                                    <Button variant="primary">
                                                        5
                                                    </Button>
                                                </Tab>
                                                <Tab>
                                                    Schedule{" "}
                                                    <Button variant="primary">
                                                        7
                                                    </Button>
                                                </Tab>
                                                <Tab>
                                                    Approvals{" "}
                                                    <Button variant="primary">
                                                        3
                                                    </Button>
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
