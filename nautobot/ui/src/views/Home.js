import {
    AutomationIcon,
    DcimIcon,
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
import HomeChangelogPanel from "@components/HomeChangelogPanel";
import HomePanel from "@components/HomePanel";
import JobHistoryTable from "@components/JobHistoryTable";
import { useGetRESTAPIQuery } from "@utils/api";
import GenericView from "@views/generic/GenericView";

export default function Home() {
    const { data: jobResultData } = useGetRESTAPIQuery({
        app_name: "extras",
        model_name: "job-results",
        limit: 1,
        depth: 0,
    });

    return (
        <GenericView columns="1 1 1 1 3 1" gridBackground="white-0">
            <HomePanel
                icon=<DcimIcon />
                title="Inventory"
                data={{
                    Racks: { app_name: "dcim", model_name: "racks" },
                    "Device Types": {
                        app_name: "dcim",
                        model_name: "device-types",
                    },
                    Devices: { app_name: "dcim", model_name: "devices" },
                    "Virtual Chassis": {
                        app_name: "dcim",
                        model_name: "virtual-chassis",
                    },
                    "Device Redundancy Groups": {
                        app_name: "dcim",
                        model_name: "device-redundancy-groups",
                    },
                    Connections: 2618,
                }}
            />
            <HomePanel
                icon=<IpamIcon />
                title="Networks"
                data={{
                    VRFs: { app_name: "ipam", model_name: "vrfs" },
                    Prefixes: { app_name: "ipam", model_name: "prefixes" },
                    "IP Addresses": {
                        app_name: "ipam",
                        model_name: "ip-addresses",
                    },
                    VLANs: { app_name: "ipam", model_name: "vlans" },
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
                    "Git Repositories": {
                        app_name: "extras",
                        model_name: "git-repositories",
                    },
                    Tags: { app_name: "extras", model_name: "tags" },
                    Statuses: { app_name: "extras", model_name: "statuses" },
                    Roles: { app_name: "extras", model_name: "roles" },
                    Relationships: {
                        app_name: "extras",
                        model_name: "relationships",
                    },
                    "Computed Fields": {
                        app_name: "extras",
                        model_name: "computed-fields",
                    },
                    "Custom Fields": {
                        app_name: "extras",
                        model_name: "custom-fields",
                    },
                    "Custom Links": {
                        app_name: "extras",
                        model_name: "custom-links",
                    },
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
                                                    <TagLabel>
                                                        {jobResultData?.count}
                                                    </TagLabel>
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
                                                <JobHistoryTable />
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
            <HomeChangelogPanel />
        </GenericView>
    );
}
