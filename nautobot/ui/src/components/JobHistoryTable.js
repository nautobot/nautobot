import {
    AutomationIcon, // TODO
    Table,
    Tbody,
    Td,
    Tr,
} from "@nautobot/nautobot-ui";

export default function JobHistoryTable({ rows }) {
    return (
        <Table>
            <Tbody>
                {rows.map((row) => {
                    return (
                        <>
                            <Tr>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>{row["user"]}</Td>
                                <Td width="3em">
                                    <AutomationIcon />
                                </Td>
                                <Td>{row["completed"]}</Td>
                            </Tr>
                            <Tr>
                                <Td colspan={4}>{row["job"]}</Td>
                            </Tr>
                        </>
                    );
                })}
            </Tbody>
        </Table>
    );
}
