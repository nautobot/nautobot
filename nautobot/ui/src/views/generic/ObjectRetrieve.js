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
import ObjectListTable from "@components/ObjectListTable";
import { useGetRESTAPIQuery } from "@utils/api";
import { humanFriendlyDate } from "@utils/date";
import { toTitleCase } from "@utils/string";
import { uiUrl } from "@utils/url";
import RouterLink from "@components/RouterLink";
import GenericView from "@views/generic/GenericView";

const fetcher = (url) =>
    fetch(url, { credentials: "include" }).then((res) =>
        res.ok ? res.json() : null
    );

function render_header(value) {
    value = toTitleCase(value, "_");
    value = toTitleCase(value, "-");
    return value;
}

export function DetailFieldValue(value) {
    const ref = useRef();
    if (value === undefined) {
        return <>&mdash;</>;
    }
    switch (typeof value) {
        case "object":
            return value === null ? (
                <>&mdash;</>
            ) : Array.isArray(value) ? (
                value.map((v, idx) =>
                    typeof v === "object" && v !== null ? (
                        <div>
                            <RouterLink ref={ref} to={uiUrl(v.url)} key={idx}>
                                {v.display}
                            </RouterLink>
                        </div>
                    ) : (
                        <div>{v}</div>
                    )
                )
            ) : "url" in value ? (
                <RouterLink ref={ref} to={uiUrl(value.url)}>
                    {" "}
                    {value.display}{" "}
                </RouterLink>
            ) : "label" in value ? (
                <>{value.label}</>
            ) : (
                <Table>
                    <Tbody>
                        {Object.entries(value).map(([k, v]) => (
                            <Tr>
                                <Td>
                                    <strong>{k.toString()}</strong>
                                </Td>
                                <Td>
                                    {v === null
                                        ? "None"
                                        : typeof v === "object" && v !== null
                                        ? Object.entries(v).map(
                                              ([json_key, json_value]) => (
                                                  <span>
                                                      {json_key}
                                                      {": "} {json_value}
                                                  </span>
                                              )
                                          )
                                        : v.toString()}
                                </Td>
                            </Tr>
                        ))}
                    </Tbody>
                </Table>
            );
        case "boolean":
            return value ? (
                <FontAwesomeIcon icon={faCheck} />
            ) : (
                <FontAwesomeIcon icon={faXmark} />
            );
        default:
            return value === "" ? <>&mdash;</> : value;
    }
}

function RenderRow(props) {
    var key = props.identifier;
    var value = props.value;

    if (
        [
            "id",
            "url",
            "display",
            "natural_key_slug",
            "slug",
            "notes_url",
        ].includes(key) ^ !!props.advanced
    ) {
        return null;
    }

    if (key[0] === "_") return null;

    // "foo_bar" --> "Foo Bar"
    key = toTitleCase(key, "_");
    return (
        <Tr>
            <Td>{key}</Td>
            <Td>{DetailFieldValue(value)}</Td>
        </Tr>
    );
}

export default function ObjectRetrieve({ api_url }) {
    const { app_label, model_name, object_id } = useParams();
    const { isOpen, onClose, onOpen } = useDisclosure();
    const location = useLocation();
    const isPluginView = location.pathname.includes("/plugins/");
    const pluginPrefix = isPluginView ? "plugins/" : "";
    if (!!app_label && !!model_name && !!object_id && !api_url) {
        api_url = `/api/${pluginPrefix}${app_label}/${model_name}/${object_id}/?depth=1`;
    }
    // const { data: appHTML } = useSWR(
    //     () => (api_url ? api_url + "app_full_width_fragment/" : null),
    //     fetcherHTML
    // );

    // Object Data
    const {
        data: objectData,
        isError: error,
        isLoading: objectDataLoading,
    } = useSWR(() => api_url, fetcher);
    const ui_url = objectData?.url
        ? `${objectData.url}detail-view-config/`
        : null;
    var { data: appConfig } = useSWR(() => ui_url, fetcher);
    // ChangeLog Data
    const changelog_url = `/api/extras/object-changes/?changed_object_id=${object_id}&depth=1`;
    const {
        data: changelogData,
        isError: changelog_error,
        isLoading: changelogDataLoading,
        isFetching: changelogDataFetching,
    } = useSWR(() => changelog_url, fetcher);
    const {
        data: changelogHeaderData,
        isFetching: changelogHeaderDataFetching,
        isLoading: changelogHeaderDataLoading,
    } = useGetRESTAPIQuery({
        app_label: "extras",
        model_name: "object-changes",
        schema: true,
    });
    // Note Data
    const notes_url = `/api/${pluginPrefix}${app_label}/${model_name}/${object_id}/notes/`;
    const {
        data: noteData,
        isError: note_error,
        isLoading: noteDataLoading,
        isFetching: noteDataFetching,
    } = useSWR(() => notes_url, fetcher);
    const {
        data: noteHeaderData,
        isFetching: noteHeaderDataFetching,
        isLoading: noteHeaderDataLoading,
    } = useGetRESTAPIQuery({
        app_label: "extras",
        model_name: "notes",
        schema: true,
    });

    if (error || note_error || changelog_error) {
        return (
            <GenericView objectData={objectData}>
                <div>Failed to load {api_url}</div>
            </GenericView>
        );
    }

    if (objectDataLoading || !objectData || !appConfig) {
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
    const route_name = `${app_label}:${model_name}`;
    let obj = objectData;
    let changelogDataLoaded =
        !(changelogDataLoading || changelogDataFetching) &&
        !(changelogHeaderDataLoading || changelogHeaderDataFetching);
    let noteDataLoaded =
        !(noteDataLoading || noteDataFetching) &&
        !(noteHeaderDataLoading || noteHeaderDataFetching);
    const default_view = (
        <GenericView objectData={objectData}>
            <Box background="white-0" borderRadius="md">
                <Box display="flex" justifyContent="space-between" padding="md">
                    <Heading display="flex" alignItems="center" gap="5px">
                        <NtcThumbnailIcon width="25px" height="30px" />{" "}
                        <Text size="H1" as="h1">
                            {obj.display}
                        </Text>
                        {obj.status && (
                            <Box p={2} flexGrow="1">
                                <Text size="P2">
                                    <ReferenceDataTag
                                        model_name="statuses"
                                        id={obj.status.id}
                                        variant="unknown"
                                        size="sm"
                                    />
                                </Text>
                            </Box>
                        )}
                        {obj.created && (
                            <Box p={2} flexGrow="1">
                                <Text size="P2" color="gray-2">
                                    <FontAwesomeIcon icon={faCalendarPlus} />
                                    {humanFriendlyDate(obj.created)}
                                </Text>
                            </Box>
                        )}
                        {obj.last_updated && (
                            <Box p={2} flexGrow="1">
                                <Text size="P2" color="gray-2">
                                    <FontAwesomeIcon icon={faPencil} />
                                    {humanFriendlyDate(obj.last_updated)}
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

                <Tabs>
                    <TabList pl="md">
                        {Object.keys(appConfig).map((key, idx) => (
                            <Tab key={idx}>{render_header(key)}</Tab>
                        ))}
                        <Tab>Notes</Tab>
                        <Tab>Change Log</Tab>
                    </TabList>
                    <TabPanels>
                        {Object.keys(appConfig).map((tab, idx) => (
                            <TabPanel padding="none" key={tab}>
                                <Card>
                                    <NautobotGrid row={{ count: 5 }}>
                                        {Object.keys(appConfig[tab]).map(
                                            (item, idx) => (
                                                <NautobotGridItem
                                                    colSpan={
                                                        appConfig[tab][item]
                                                            .colspan
                                                    }
                                                    rowSpan={
                                                        appConfig[tab][item]
                                                            .rowspan
                                                    }
                                                    key={idx}
                                                >
                                                    <Heading
                                                        display="flex"
                                                        alignItems="center"
                                                    >
                                                        <NtcThumbnailIcon
                                                            width="25px"
                                                            height="30px"
                                                        />
                                                        &nbsp;
                                                        {render_header(
                                                            appConfig[tab][item]
                                                                .name
                                                        )}
                                                    </Heading>
                                                    <br />
                                                    <TableContainer>
                                                        <Table>
                                                            <Tbody>
                                                                {Object.keys(
                                                                    appConfig[
                                                                        tab
                                                                    ][item]
                                                                        .fields
                                                                ).map(
                                                                    (
                                                                        key,
                                                                        idx
                                                                    ) => (
                                                                        <RenderRow
                                                                            identifier={
                                                                                appConfig[
                                                                                    tab
                                                                                ][
                                                                                    item
                                                                                ]
                                                                                    .fields[
                                                                                    key
                                                                                ]
                                                                            }
                                                                            value={
                                                                                obj[
                                                                                    appConfig[
                                                                                        tab
                                                                                    ][
                                                                                        item
                                                                                    ]
                                                                                        .fields[
                                                                                        key
                                                                                    ]
                                                                                ]
                                                                            }
                                                                            advanced={
                                                                                appConfig[
                                                                                    tab
                                                                                ][
                                                                                    item
                                                                                ]
                                                                                    .advanced
                                                                            }
                                                                            key={`${tab}_${idx}`}
                                                                        />
                                                                    )
                                                                )}
                                                            </Tbody>
                                                        </Table>
                                                    </TableContainer>
                                                </NautobotGridItem>
                                            )
                                        )}
                                    </NautobotGrid>
                                </Card>
                            </TabPanel>
                        ))}
                        <TabPanel key="notes">
                            <Card>
                                <CardHeader>
                                    <Heading
                                        display="flex"
                                        alignItems="center"
                                        gap="5px"
                                    >
                                        <NtcThumbnailIcon
                                            width="25px"
                                            height="30px"
                                        />{" "}
                                        Notes
                                    </Heading>
                                </CardHeader>
                                <ObjectListTable
                                    tableData={noteData.results}
                                    defaultHeaders={
                                        noteHeaderData.view_options
                                            .list_display_fields
                                    }
                                    tableHeaders={
                                        noteHeaderData.view_options.fields
                                    }
                                    totalCount={noteData.count}
                                    active_page_number={0}
                                    page_size={50}
                                    tableTitle={"Notes"}
                                    include_button={false}
                                    data_loaded={noteDataLoaded}
                                    data_fetched={!noteDataFetching}
                                />
                            </Card>
                        </TabPanel>
                        <TabPanel key="change_log">
                            <Card>
                                <CardHeader>
                                    <Heading
                                        display="flex"
                                        alignItems="center"
                                        gap="5px"
                                    >
                                        <NtcThumbnailIcon
                                            width="25px"
                                            height="30px"
                                        />{" "}
                                        Change Log
                                    </Heading>
                                </CardHeader>
                                <ObjectListTable
                                    tableData={changelogData.results}
                                    defaultHeaders={
                                        changelogHeaderData.view_options
                                            .list_display_fields
                                    }
                                    tableHeaders={
                                        changelogHeaderData.view_options.fields
                                    }
                                    totalCount={changelogData.count}
                                    active_page_number={0}
                                    page_size={50}
                                    tableTitle={"Change Logs"}
                                    include_button={false}
                                    data_loaded={changelogDataLoaded}
                                    data_fetched={!changelogDataFetching}
                                />
                            </Card>
                        </TabPanel>
                    </TabPanels>
                </Tabs>
            </Box>
        </GenericView>
    );
    let return_view = default_view;
    if (
        AppComponents.CustomViews?.[route_name] &&
        "retrieve" in AppComponents.CustomViews?.[route_name]
    ) {
        const CustomView = AppComponents.CustomViews[route_name].retrieve;
        return_view = <CustomView {...obj} />;
    }

    return return_view;
}
