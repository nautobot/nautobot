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
import { RouterLink } from "@components/RouterLink";
import { toTitleCase } from "@utils/string";

function HomePanelCountTag(count = 0) {
    return (
        <Tag size="sm" variant={count ? "info" : "unknown"}>
            <TagLabel>{count}</TagLabel>
        </Tag>
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
                            <Th colSpan={2}>{title}</Th>
                        </Tr>
                    </Thead>
                    <Tbody>
                        {data.map((row, idx) => (
                            <Tr key={idx}>
                                <Td colSpan={2}>
                                    {row.url ? (
                                        <RouterLink to={row.url}>
                                            {toTitleCase(row["name"])}
                                        </RouterLink>
                                    ) : (
                                        toTitleCase(row["name"])
                                    )}
                                </Td>
                                <Td width="4em" textAlign="right">
                                    {HomePanelCountTag(row.count)}
                                </Td>
                            </Tr>
                        ))}
                    </Tbody>
                </Table>
            </TableContainer>
        </NautobotGridItem>
    );
}
