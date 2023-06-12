import { Table, Tbody, Td, Tr } from "@nautobot/nautobot-ui";

import { ObjectTableItem } from "@components";
import { buildUrl } from "@utils/url";

function RenderTable({ fields, schema, data }) {
    return (
        <Table>
            <Tbody>
                {fields.map((fieldName, idx) => {
                    const fieldSchema = schema[fieldName];
                    const fieldData = data[fieldName];
                    let url = null;
                    if (fieldSchema?.appLabel) {
                        url = buildUrl(
                            fieldSchema.appLabel,
                            fieldSchema.modelName,
                            fieldData?.id
                        );
                    }
                    return (
                        <Tr key={idx}>
                            <Td>{fieldSchema.title}</Td>
                            <Td>
                                <ObjectTableItem obj={fieldData} url={url} />
                            </Td>
                        </Tr>
                    );
                })}
            </Tbody>
        </Table>
    );
}

export default RenderTable;
