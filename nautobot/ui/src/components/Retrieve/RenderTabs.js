import { Tab, Tabs, TabList, TabPanel, TabPanels } from "@nautobot/nautobot-ui";

import { RenderColumn, RenderNotesTab, RenderChangeLogsTab } from ".";

function RenderTabs({
    layoutSchema,
    schema,
    data,
    app_label,
    model_name,
    object_id,
    isPluginView,
}) {
    return (
        <Tabs>
            <TabList pl="md">
                {Object.entries(layoutSchema.tabs).map(([tabTitle], idx) => (
                    <Tab key={idx}>{tabTitle}</Tab>
                ))}
                <Tab>Notes</Tab>
                <Tab>Change Logs</Tab>
            </TabList>
            <TabPanels>
                {Object.entries(layoutSchema.tabs).map(([_, tabData], idx) => (
                    <TabPanel key={idx}>
                        <RenderColumn
                            tabData={tabData}
                            data={data}
                            schema={schema}
                        />
                    </TabPanel>
                ))}
                <TabPanel>
                    <RenderNotesTab
                        app_label={app_label}
                        model_name={model_name}
                        object_id={object_id}
                        isPluginView={isPluginView}
                    />
                </TabPanel>
                <TabPanel>
                    <RenderChangeLogsTab object_id={object_id} />
                </TabPanel>
            </TabPanels>
        </Tabs>
    );
}

export default RenderTabs;
