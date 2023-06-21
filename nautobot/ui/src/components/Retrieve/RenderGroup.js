import { Card, CardHeader } from "@chakra-ui/react"; // TODO: use nautobot-ui when available
import {
    Heading,
    TableContainer,
    NtcThumbnailIcon,
} from "@nautobot/nautobot-ui";

import RenderTable from "./RenderTable";

function RenderGroup({ fields, title, schema, data }) {
    return (
        <Card marginBottom="10">
            <CardHeader marginBottom="3">
                <Heading display="flex" alignItems="center" gap="5px">
                    <NtcThumbnailIcon width="25px" height="30px" /> {title}
                </Heading>
            </CardHeader>
            <TableContainer>
                <RenderTable fields={fields} schema={schema} data={data} />
            </TableContainer>
        </Card>
    );
}

export default RenderGroup;
