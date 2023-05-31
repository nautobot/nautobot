import useSWR from "swr";
import { useRef } from "react";
import { useLocation, useParams } from "react-router-dom";

import {
    faCheck,
    faCalendarPlus,
    faPencil,
    faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    Card,
    CardHeader,
    SkeletonText,
    useDisclosure,
} from "@chakra-ui/react"; // TODO: use nautobot-ui when available
import {
    Box,
    Button as UIButton,
    ButtonGroup,
    Heading,
    Tab,
    Tabs,
    TabList,
    TabPanel,
    TabPanels,
    Table,
    TableContainer,
    Tbody,
    Td,
    Tr,
    Text,
    MeatballsIcon,
    Modal,
    ModalBody,
    ModalCloseButton,
    ModalContent,
    ModalOverlay,
    NautobotGrid,
    NautobotGridItem,
    NtcThumbnailIcon,
} from "@nautobot/nautobot-ui";

import AppComponents from "@components/Apps";
import { ReferenceDataTag } from "@components/ReferenceDataTag";
import TableItem from "@components/TableItem";
import ObjectListTable from "@components/ObjectListTable";
import { useGetRESTAPIQuery } from "@utils/api";
import { humanFriendlyDate } from "@utils/date";
import { toTitleCase } from "@utils/string";
import { uiUrl, buildUrl } from "@utils/url";
import RouterLink from "@components/RouterLink";
import GenericView from "@views/generic/GenericView";

function ObjectRetrieveHeading({ data }) {
    const { isOpen, onClose, onOpen } = useDisclosure();
    return (
        <Box display="flex" justifyContent="space-between" padding="md">
            <Heading display="flex" alignItems="center" gap="5px">
                <NtcThumbnailIcon width="25px" height="30px" />{" "}
                <Text size="H1" as="h1">
                    {data.display}
                </Text>
                {data.status && (
                    <Box p={2} flexGrow="1">
                        <Text size="P2">
                            <ReferenceDataTag
                                model_name="statuses"
                                id={data.status.id}
                                variant="unknown"
                                size="sm"
                            />
                        </Text>
                    </Box>
                )}
                {data.created && (
                    <Box p={2} flexGrow="1">
                        <Text size="P2" color="gray-2">
                            <FontAwesomeIcon icon={faCalendarPlus} />
                            {humanFriendlyDate(data.created)}
                        </Text>
                    </Box>
                )}
                {data.last_updated && (
                    <Box p={2} flexGrow="1">
                        <Text size="P2" color="gray-2">
                            <FontAwesomeIcon icon={faPencil} />
                            {humanFriendlyDate(data.last_updated)}
                        </Text>
                    </Box>
                )}
            </Heading>
            <ButtonGroup alignItems="center">
                <UIButton
                    size="sm"
                    variant="primaryAction"
                    leftIcon={<MeatballsIcon />}
                    onClick={onOpen}
                >
                    Actions
                </UIButton>

                <Modal isOpen={isOpen} onClose={onClose}>
                    <ModalOverlay />

                    <ModalContent>
                        <ModalCloseButton />

                        <ModalBody>To be implemented!</ModalBody>
                    </ModalContent>
                </Modal>
            </ButtonGroup>
        </Box>
    );
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
                            fieldSchema.modelName,
                            fieldData?.id
                        );
                    }
                    return (
                        <Tr key={idx}>
                            <Td>{fieldSchema?.title}</Td>
                            <Td>
                                <TableItem obj={fieldData} url={url} />
                            </Td>
                        </Tr>
                    );
                })}
            </Tbody>
        </Table>
    );
}

function RenderGroup({ fields, title, schema, data }) {
    return (
        <Card marginBottom="10">
            <CardHeader marginBottom="3">
                <Heading display="flex" alignItems="center" gap="5px">
                    <NtcThumbnailIcon width="25px" height="30px" /> {title}
                </Heading>
            </CardHeader>
            <TableContainer>
                <RenderTable fields={fields} schema={schema} data={data} />
            </TableContainer>
        </Card>
    );
}

function RenderCol({ tabData, data, schema }) {
    return (
        <NautobotGrid columns="2">
            {tabData.map((group, idx) => (
                <NautobotGridItem key={idx}>
                    {Object.entries(group).map(([title, { fields }], idx) => (
                        <RenderGroup
                            fields={fields}
                            data={data}
                            schema={schema}
                            title={title}
                        />
                    ))}
                </NautobotGridItem>
            ))}
        </NautobotGrid>
    );
}

function RenderTabs({ layoutSchema, schema, data }) {
    return (
        <Tabs>
            <TabList pl="md">
                {Object.entries(layoutSchema.tabs).map(([tabTitle], idx) => (
                    <Tab key={idx}>{tabTitle}</Tab>
                ))}
            </TabList>
            <TabPanels>
                {Object.entries(layoutSchema.tabs).map(([_, tabData], idx) => (
                    <TabPanel key={idx}>
                        <RenderCol
                            tabData={tabData}
                            data={data}
                            schema={schema}
                        />
                    </TabPanel>
                ))}
            </TabPanels>
        </Tabs>
    );
}

export default function ObjectRetrieve({ api_url }) {
    const { app_label, model_name, object_id } = useParams();
    const location = useLocation();
    const isPluginView = location.pathname.includes("/plugins/");
    const pluginPrefix = isPluginView ? "plugins/" : "";
    const { data, isLoading, isError } = useGetRESTAPIQuery({
        app_label,
        model_name,
        uuid: object_id,
    });
    const {
        data: schemaData,
        isLoading: schemaIsLoading,
        isError: schemaIsError,
    } = useGetRESTAPIQuery({
        app_label,
        model_name,
        uuid: object_id,
        schema: true,
    });
    const route_name = `${app_label}:${model_name}`;

    if (isLoading || schemaIsLoading) {
        return (
            <GenericView>
                <SkeletonText
                    endColor="gray.300"
                    noOfLines={10}
                    skeletonHeight="25"
                    spacing="3"
                    mt="3"
                ></SkeletonText>
            </GenericView>
        );
    }

    if (isError || schemaIsError) {
        return (
            <GenericView objectData={data}>
                <div>Failed to load {api_url}</div>
            </GenericView>
        );
    }

    if (
        AppComponents.CustomViews?.[route_name] &&
        "retrieve" in AppComponents.CustomViews?.[route_name]
    ) {
        const CustomView = AppComponents.CustomViews[route_name].retrieve;
        return <CustomView {...data} />;
    }

    const objectRetrieveTabSchema = {
        tabs: {
            Location: schemaData.view_options.retrieve,
            Notes: [],
            "Change Logs": [],
        },
    };

    return (
        <GenericView objectData={data}>
            <Box background="white-0" borderRadius="md">
                <ObjectRetrieveHeading data={data} />
                <RenderTabs
                    schema={schemaData.schema.properties}
                    layoutSchema={objectRetrieveTabSchema}
                    data={data}
                />
            </Box>
        </GenericView>
    );
}
