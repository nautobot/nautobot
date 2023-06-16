import { NautobotGrid, NautobotGridItem } from "@nautobot/nautobot-ui";

import RenderGroup from "./RenderGroup";

function RenderColumn({ tabData, data, schema }) {
    return (
        <NautobotGrid columns="2">
            {tabData.map((group, idx) => (
                <NautobotGridItem key={idx}>
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
