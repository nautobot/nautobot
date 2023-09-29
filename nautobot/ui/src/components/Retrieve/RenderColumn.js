import { NautobotGrid, NautobotGridItem } from "@nautobot/nautobot-ui";

import RenderGroup from "./RenderGroup";

function RenderColumn({ tabData, data, schema }) {
    return (
        <NautobotGrid columns="2" padding={0}>
            {tabData.map((group, idx) => (
                <NautobotGridItem
                    key={idx}
                    flexDirection="column"
                    display="flex"
                    gap="md"
                >
                    {Object.entries(group).map(([title, { fields }], idx) => (
                        <RenderGroup
                            key={idx}
                            fields={fields}
                            data={data}
                            schema={schema}
                            title={title}
                        />
                    ))}
                </NautobotGridItem>
            ))}
        </NautobotGrid>
    );
}

export default RenderColumn;
