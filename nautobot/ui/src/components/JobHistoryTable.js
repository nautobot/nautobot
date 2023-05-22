import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faClock, faUser } from "@fortawesome/free-solid-svg-icons";
import { Table, Tag, TagLabel, Tbody, Td, Tr } from "@nautobot/nautobot-ui";
import { useGetRESTAPIQuery } from "@utils/api";
import { humanFriendlyDate } from "@utils/date";

function jobResultStatusTag(status) {
    let variant = "unknown";
    switch (status) {
        case "FAILURE":
        case "REVOKED":
            variant = "critical";
            break;
        case "PENDING":
        case "RECEIVED":
            variant = "secondary";
            break;
        case "RETRY":
            variant = "action";
            break;
        case "STARTED":
            variant = "info";
            break;
        case "SUCCESS":
            variant = "success";
            break;
        default:
            variant = "unknown";
            break;
    }
    return (
        <Tag variant={variant}>
            <TagLabel>{status}</TagLabel>
        </Tag>
    );
}

export default function JobHistoryTable() {
    const { data, isError } = useGetRESTAPIQuery({
        app_label: "extras",
        model_name: "job-results",
        limit: 10,
        depth: 1,
    });

    if (isError) {
        return "TODO";
    }

    return (
        <Table>
            <Tbody>
                {data?.results?.map((result) => {
                    return [
                        <Tr key={result.id + "row_1"}>
                            <Td width="2em">
                                <FontAwesomeIcon icon={faUser} />
                            </Td>
                            <Td>{result.user?.username}</Td>
                            <Td width="2em">
                                <FontAwesomeIcon icon={faClock} />
                            </Td>
                            <Td>{humanFriendlyDate(result.date_done)}</Td>
                            <Td textAlign="right">
                                {jobResultStatusTag(result.status.value)}
                            </Td>
                        </Tr>,
                        <Tr key={result.id + "row_2"}>
                            <Td colSpan={5}>
                                {result.job_model?.display || result.name}
                            </Td>
                        </Tr>,
                    ];
                })}
            </Tbody>
        </Table>
    );
}
