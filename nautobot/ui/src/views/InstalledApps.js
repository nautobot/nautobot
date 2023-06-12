import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faBookOpen, faGear, faHome } from "@fortawesome/free-solid-svg-icons";
import {
    Button,
    Link,
    Table,
    TableContainer,
    Tbody,
    Td,
    Th,
    Thead,
    Tr,
} from "@nautobot/nautobot-ui";
import { useGetRESTAPIQuery } from "@utils/api";
import GenericView from "@views/generic/GenericView";

export default function InstalledApps() {
    const { data, isLoading } = useGetRESTAPIQuery({
        app_label: "plugins",
        model_name: "installed-plugins",
    });

    if (isLoading) {
        return <GenericView gridBackground="white-0" />;
    }

    return (
        <GenericView gridBackground="white-0">
            <TableContainer>
                <Table>
                    <Thead>
                        <Tr>
                            <Th>Name</Th>
                            <Th>Description</Th>
                            <Th>Version</Th>
                            <Th>Links</Th>
                        </Tr>
                    </Thead>
                    <Tbody>
                        {Object.values(data).map((app) => (
                            <Tr>
                                <Td>{app.name}</Td>
                                <Td>{app.description}</Td>
                                <Td>{app.version}</Td>
                                <Td>
                                    <Link href={app.home_url}>
                                        <Button
                                            variant="primary"
                                            isDisabled={!app.home_url}
                                        >
                                            <FontAwesomeIcon icon={faHome} />
                                        </Button>
                                    </Link>
                                    <Link href={app.config_url}>
                                        <Button
                                            variant="primaryAction"
                                            isDisabled={!app.config_url}
                                        >
                                            <FontAwesomeIcon icon={faGear} />
                                        </Button>
                                    </Link>
                                    <Link href={app.docs_url}>
                                        <Button
                                            variant="primary"
                                            isDisabled={!app.docs_url}
                                        >
                                            <FontAwesomeIcon
                                                icon={faBookOpen}
                                            />
                                        </Button>
                                    </Link>
                                </Td>
                            </Tr>
                        ))}
                    </Tbody>
                </Table>
            </TableContainer>
        </GenericView>
    );
}
