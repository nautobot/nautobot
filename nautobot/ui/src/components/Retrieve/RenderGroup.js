import {
    Flex,
    Heading,
    NtcThumbnailIcon,
    TableContainer,
} from "@nautobot/nautobot-ui";

import RenderTable from "./RenderTable";

function RenderGroup({ fields, title, schema, data }) {
    return (
        <Flex as="section" direction="column" gap="md">
            <Heading alignItems="center" display="flex" gap="xs">
                <NtcThumbnailIcon height="auto" width="24" />
                {title}
            </Heading>
            <TableContainer>
                <RenderTable fields={fields} schema={schema} data={data} />
            </TableContainer>
        </Flex>
    );
}

export default RenderGroup;
