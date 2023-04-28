import {
    Link,
    NautobotGridItem,
    Table,
    TableContainer,
    Tag,
    TagLabel,
    Tbody,
    Td,
    Th,
    Thead,
    Tr,
} from "@nautobot/nautobot-ui";
import { useGetRESTAPIQuery } from "@utils/api";

function HomePanelData(attrs) {
    const { data, isLoading, isError } = useGetRESTAPIQuery({
        app_name: attrs["app_name"],
        model_name: attrs["model_name"],
        limit: 1,
        depth: 0,
    });

    if (isLoading) {
        return (
            <Tag size="sm" variant="unknown">
                <TagLabel>Loading...</TagLabel>
            </Tag>
        );
    }
    if (isError) {
        return (
            <Tag size="sm" variant="critical">
                <TagLabel>Unknown</TagLabel>
            </Tag>
        );
    }

    if (data.count) {
        return (
            <Link href={`/${attrs["app_name"]}/${attrs["model_name"]}/`}>
                <Tag size="sm" variant="info">
                    <TagLabel>{data.count}</TagLabel>
                </Tag>
            </Link>
        );
    }
    return (
        <Link href={`/${attrs["app_name"]}/${attrs["model_name"]}/`}>
            <Tag size="sm" variant="unknown">
                <TagLabel>{data.count}</TagLabel>
            </Tag>
        </Link>
    );
}

// A panel in the Home view displaying a table of objects and their counts.
export default function HomePanel({ icon, title, data }) {
    return (
        <NautobotGridItem>
            <TableContainer>
                <Table>
                    <Thead>
                        <Tr _hover={{}}>
                            <Th width="3em">{icon}</Th>
                            <Th colspan={2}>{title}</Th>
                        </Tr>
                    </Thead>
                    <Tbody>
                        {Object.entries(data).map((row) => (
                            <Tr>
                                <Td colspan={2}>{row[0]}</Td>
                                <Td
                                    width="4em"
                                    style={{ "text-align": "right" }}
                                >
                                    {typeof row[1] === "number" ? (
                                        row[1] === 0 ? (
                                            <Tag size="sm" variant="unknown">
                                                <TagLabel>{row[1]}</TagLabel>
                                            </Tag>
                                        ) : (
                                            <Tag size="sm" variant="info">
                                                <TagLabel>{row[1]}</TagLabel>
                                            </Tag>
                                        )
                                    ) : (
                                        HomePanelData(row[1])
                                    )}
                                </Td>
                            </Tr>
                        ))}
                    </Tbody>
                </Table>
            </TableContainer>
        </NautobotGridItem>
    );
}
