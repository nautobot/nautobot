import { Table, Tbody, Td, Tr } from "@nautobot/nautobot-ui";

import { ObjectTableItem } from "@components";
import { buildUrl } from "@utils/url";

function construct_model_url(model_title) {
    // helper function to turn plural model names to url safe strings
    // e.g. tenant groups -> tenant-groups
    var model_url = model_title;
    model_url = model_url.replace(/\s+/g, "-").toLowerCase();
    return model_url;
}

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
                            construct_model_url(fieldSchema?.modelNamePlural),
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
