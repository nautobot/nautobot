import {
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
                                    {row[1] ? (
                                        <Tag size="sm" variant="info">
                                            <TagLabel>{row[1]}</TagLabel>
                                        </Tag>
                                    ) : (
                                        <Tag size="sm" variant="unknown">
                                            <TagLabel>{row[1]}</TagLabel>
                                        </Tag>
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
