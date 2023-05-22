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
import { humanFriendlyDate } from "@utils/date";
import { uiUrl } from "@utils/url";

export default function HomeChangelogPanel() {
    const { data, isError } = useGetRESTAPIQuery({
        app_label: "extras",
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
                            <Th colSpan={4}>Change Log</Th>
                        </Tr>
                    </Thead>
                    <Tbody>
                        {data?.results?.map((objectChange) => [
                            <Tr key={objectChange.id + "row_1"}>
                                <Td width="2em">
                                    <FontAwesomeIcon icon={faUser} />
                                </Td>
                                <Td>{objectChange.user_name}</Td>
                                <Td width="2em">
                                    <FontAwesomeIcon icon={faClock} />
                                </Td>
                                <Td>{humanFriendlyDate(objectChange.time)}</Td>
                                <Td>
                                    <Tag
                                        variant={
                                            objectChange.action.label ===
                                            "Created"
                                                ? "success"
                                                : objectChange.action.label ===
                                                  "Deleted"
                                                ? "critical"
                                                : "info"
                                        }
                                    >
                                        <TagLabel>
                                            {objectChange.action.label}
                                        </TagLabel>
                                    </Tag>
                                </Td>
                            </Tr>,
                            <Tr key={objectChange.id + "row_2"}>
                                <Td colSpan={2}>
                                    {objectChange.changed_object_type}
                                </Td>
                                <Td colSpan={3}>
                                    {objectChange.changed_object ? (
                                        <Link
                                            href={uiUrl(
                                                objectChange.changed_object.url
                                            )}
                                        >
                                            {objectChange.object_repr}
                                        </Link>
                                    ) : (
                                        objectChange.object_repr
                                    )}
                                </Td>
                            </Tr>,
                        ])}
                    </Tbody>
                </Table>
            </TableContainer>
        </NautobotGridItem>
    );
}
