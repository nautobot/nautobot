import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faClock, faUser } from "@fortawesome/free-solid-svg-icons";
import {
    HistoryIcon,
    Link,
    NautobotGridItem,
    TableContainer,
    Table,
    Tag,
    TagLabel,
    Tbody,
    Td,
    Th,
    Thead,
    Tr,
} from "@nautobot/nautobot-ui";
import { useGetRESTAPIQuery } from "@utils/api";

function humanFriendlyDate(dateStr) {
    const date = new Date(dateStr);
    return (
        date.getFullYear().toString() +
        "-" +
        date.getMonth().toString().padStart(2, "0") +
        "-" +
        date.getDate().toString().padStart(2, "0") +
        " " +
        date.getHours().toString().padStart(2, "0") +
        ":" +
        date.getMinutes().toString().padStart(2, "0")
    );
}

export default function HomeChangelogPanel() {
    const { data, isError } = useGetRESTAPIQuery({
        app_name: "extras",
        model_name: "object-changes",
        limit: 10,
        depth: 1,
    });

    if (isError) {
        return <NautobotGridItem>TODO</NautobotGridItem>;
    }

    return (
        <NautobotGridItem>
            <TableContainer>
                <Table>
                    <Thead>
                        <Tr _hover={{}}>
                            <Th width="3em">
                                <HistoryIcon />
                            </Th>
                            <Th colspan={4}>Change Log</Th>
                        </Tr>
                    </Thead>
                    <Tbody>
                        {data?.results?.map((objectChange) => (
                            <>
                                <Tr>
                                    <Td width="2em">
                                        <FontAwesomeIcon icon={faUser} />
                                    </Td>
                                    <Td>{objectChange.user_name}</Td>
                                    <Td width="2em">
                                        <FontAwesomeIcon icon={faClock} />
                                    </Td>
                                    <Td>
                                        {humanFriendlyDate(objectChange.time)}
                                    </Td>
                                    <Td>
                                        <Tag
                                            variant={
                                                objectChange.action.label ===
                                                "Created"
                                                    ? "success"
                                                    : objectChange.action
                                                          .label === "Deleted"
                                                    ? "critical"
                                                    : "info"
                                            }
                                        >
                                            <TagLabel>
                                                {objectChange.action.label}
                                            </TagLabel>
                                        </Tag>
                                    </Td>
                                </Tr>
                                <Tr>
                                    <Td colspan={2}>
                                        {objectChange.changed_object_type}
                                    </Td>
                                    <Td colspan={3}>
                                        <Link
                                            href={
                                                objectChange.changed_object
                                                    .web_url
                                            }
                                        >
                                            {objectChange.object_repr}
                                        </Link>
                                    </Td>
                                </Tr>
                            </>
                        ))}
                    </Tbody>
                </Table>
            </TableContainer>
        </NautobotGridItem>
    );
}
