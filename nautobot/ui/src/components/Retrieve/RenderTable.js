import { Table, Tbody, Td, Tr } from "@nautobot/nautobot-ui";

import { ObjectTableItem } from "@components";

function RenderTable({ fields, schema, data }) {
    return (
        <Table>
            <Tbody>
                {fields.map((fieldName, idx) => {
                    const fieldSchema = schema[fieldName];
                    if (!fieldSchema) {
                        return "";
                    }
                    const fieldData = data[fieldName];
                    let url = null;
                    if (fieldSchema?.modelUrl && fieldData?.id) {
                        url = fieldSchema.modelUrl + fieldData.id + "/";
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
