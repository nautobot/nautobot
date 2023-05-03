import { Card, CardHeader } from "@chakra-ui/react"; // TODO: use nautobot-ui when available
import {
    faCheck,
    faCalendarPlus,
    faPencil,
    faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    Box,
    Button as UIButton,
    ButtonGroup,
    Heading,
    Link,
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
    NautobotGrid,
    NautobotGridItem,
    NtcThumbnailIcon,
} from "@nautobot/nautobot-ui";
import { ReferenceDataTag } from "@components/ReferenceDataTag";
import { useLocation, useParams } from "react-router-dom";
import useSWR from "swr";
import { useRef } from "react";
// import AppFullWidthComponentsWithProps from "@components/AppFullWidthComponents";
import AppComponents from "@components/Apps";
import { LoadingWidget } from "@components/LoadingWidget";
import { toTitleCase } from "@utils/string";
import GenericView from "@views/generic/GenericView";
import ObjectListTable from "@components/ObjectListTable";
import { useGetRESTAPIQuery } from "@utils/api";
import { humanFriendlyDate } from "@utils/date";
import { uiUrl } from "@utils/url";

const fetcher = (url) =>
    fetch(url, { credentials: "include" }).then((res) =>
        res.ok ? res.json() : null
    );
// const fetcherHTML = (url) =>
//     fetch(url, { credentials: "include" }).then((res) =>
//         res.ok ? res.text() : null
//     );
// const fetcherTabs = (url) =>
//     fetch(url, { credentials: "include" }).then((res) => {
//         return res.json().then((data) => {
//             let tabs = data.tabs.map((tab_top) =>
//                 Object.keys(tab_top).map(function (tab_key) {
//                     let tab = tab_top[tab_key];
//                     let tab_component = create_app_tab({ tab: tab });
//                     return tab_component;
//                 })
//             );
//             return tabs;
//         });
//     });

function render_header(value) {
    value = toTitleCase(value, "_");
    value = toTitleCase(value, "-");
    return value;
}

function DetailFieldValue(value) {
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
                            <Link ref={ref} href={uiUrl(v.url)} key={idx}>
                                {v.display}
                            </Link>
                        </div>
                    ) : (
                        <div>{v}</div>
                    )
                )
            ) : "url" in value ? (
                <Link ref={ref} href={uiUrl(value.url)}>
                    {" "}
                    {value.display}{" "}
                </Link>
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
        ["id", "url", "display", "slug", "notes_url"].includes(key) ^
        !!props.advanced
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
    const { app_name, model_name, object_id } = useParams();
    const location = useLocation();
    const isPluginView = location.pathname.includes("/plugins/");
    const pluginPrefix = isPluginView ? "plugins/" : "";
    if (!!app_name && !!model_name && !!object_id && !api_url) {
        api_url = `/api/${pluginPrefix}${app_name}/${model_name}/${object_id}/?depth=1`;
    }
    const { data: objectData, error } = useSWR(() => api_url, fetcher);
    // const { data: appHTML } = useSWR(
    //     () => (api_url ? api_url + "app_full_width_fragment/" : null),
    //     fetcherHTML
    // );

    // Object Data
    const ui_url = objectData?.url
        ? `${objectData.url}detail-view-config/`
        : null;
    var { data: appConfig } = useSWR(() => ui_url, fetcher);
    // ChangeLog Data
    const changelog_url = `/api/extras/object-changes/?changed_object_id=${object_id}`;
    const { data: changelogData, changelog_error } = useSWR(
        () => changelog_url,
        fetcher
    );
    const { data: changelogHeaderData, isLoading: changelogHeaderDataLoading } =
        useGetRESTAPIQuery({
            app_name: "extras",
            model_name: "object-changes",
            schema: true,
            plugin: isPluginView,
        });
    // Note Data
    const notes_url = `/api/${pluginPrefix}${app_name}/${model_name}/${object_id}/notes/`;
    const { data: noteData, note_error } = useSWR(() => notes_url, fetcher);
    const { data: noteHeaderData, isLoading: noteHeaderDataLoading } =
        useGetRESTAPIQuery({
            app_name: "extras",
            model_name: "notes",
            schema: true,
            plugin: isPluginView,
        });

    if (error || note_error || changelog_error) {
        return (
            <GenericView objectData={objectData}>
                <div>Failed to load {api_url}</div>
            </GenericView>
        );
    }

    if (!objectData || !appConfig) {
        return (
            <GenericView>
                <LoadingWidget />
            </GenericView>
        );
    }
    const route_name = `${app_name}:${model_name}`;
    let obj = objectData;
    const default_view = (
        <GenericView>
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
                        >
                            Actions
                        </UIButton>
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
                            <TabPanel
                                padding="none"
                                key={tab}
                                eventKey={tab}
                                title={render_header(tab)}
                            >
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
                                                                            key={
                                                                                idx
                                                                            }
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
                        <TabPanel key="notes" eventKey="notes" title="Notes">
                            {noteHeaderDataLoading ? (
                                <LoadingWidget name={"Notes"} />
                            ) : (
                                <Card>
                                    <CardHeader>
                                        <strong>Notes</strong>
                                    </CardHeader>
                                    <ObjectListTable
                                        tableData={noteData.results}
                                        defaultHeaders={
                                            noteHeaderData.view_options
                                                .list_display
                                        }
                                        tableHeaders={
                                            noteHeaderData.view_options.fields
                                        }
                                        totalCount={changelogData.count}
                                        active_page_number={0}
                                        page_size={50}
                                        tableTitle={"Notes"}
                                        include_button={false}
                                    />
                                </Card>
                            )}
                        </TabPanel>
                        <TabPanel
                            key="change_log"
                            eventKey="change_log"
                            title="Change Log"
                        >
                            {changelogHeaderDataLoading ? (
                                <LoadingWidget name={"Notes"} />
                            ) : (
                                <Card>
                                    <CardHeader>
                                        <strong>Change Log</strong>
                                    </CardHeader>
                                    <ObjectListTable
                                        tableData={changelogData.results}
                                        defaultHeaders={
                                            changelogHeaderData.view_options
                                                .list_display
                                        }
                                        tableHeaders={
                                            changelogHeaderData.view_options
                                                .fields
                                        }
                                        totalCount={changelogData.count}
                                        active_page_number={0}
                                        page_size={50}
                                        tableTitle={"Change Logs"}
                                        include_button={false}
                                    />
                                </Card>
                            )}
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
