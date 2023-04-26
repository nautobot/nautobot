import { Card, CardHeader } from "@chakra-ui/react"; // TODO: use nautobot-ui when available
import { faCheck, faMinus, faXmark } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
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
    NautobotGrid,
    NautobotGridItem,
    NtcThumbnailIcon,
} from "@nautobot/nautobot-ui";
import { useParams } from "react-router-dom";
import useSWR from "swr";
import { useRef } from "react";
import AppFullWidthComponentsWithProps from "@components/AppFullWidthComponents";
import create_app_tab from "@components/AppTab";
import AppComponents from "@components/Apps";
import { LoadingWidget } from "@components/LoadingWidget";
import GenericView from "@views/generic/GenericView";
import ObjectListTableNoButtons from "@components/ObjectListTableNoButtons";

const fetcher = (url) =>
    fetch(url, { credentials: "include" }).then((res) =>
        res.ok ? res.json() : null
    );
const fetcherHTML = (url) =>
    fetch(url, { credentials: "include" }).then((res) =>
        res.ok ? res.text() : null
    );
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
    value = value
        .split("_")
        .map((x) => (x ? x[0].toUpperCase() + x.slice(1) : ""))
        .join(" ");
    value = value
        .split("-")
        .map((x) => (x ? x[0].toUpperCase() + x.slice(1) : ""))
        .join(" ");
    return value;
}

function Render_value(value) {
    const ref = useRef();
    if (value === undefined) {
        return <FontAwesomeIcon icon={faMinus} />;
    }
    switch (typeof value) {
        case "object":
            return value === null ? (
                <FontAwesomeIcon icon={faMinus} />
            ) : Array.isArray(value) ? (
                value.map((v) =>
                    typeof v === "object" && v !== null ? (
                        <div>
                            <Link ref={ref} href={v["web_url"]}>
                                {v["display"]}
                            </Link>
                        </div>
                    ) : (
                        <div>{v}</div>
                    )
                )
            ) : (
                <Link ref={ref} href={value["web_url"]}>
                    {" "}
                    {value["display"]}{" "}
                </Link>
            );
        case "boolean":
            return value ? (
                <FontAwesomeIcon icon={faCheck} />
            ) : (
                <FontAwesomeIcon icon={faXmark} />
            );
        default:
            return value === "" ? <FontAwesomeIcon icon={faMinus} /> : value;
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
    key = key
        .split("_")
        .map((x) => (x ? x[0].toUpperCase() + x.slice(1) : ""))
        .join(" ");
    return (
        <Tr>
            <Td>{key}</Td>
            <Td>{Render_value(value)}</Td>
        </Tr>
    );
}

export default function ObjectRetrieve({ api_url }) {
    const { app_name, model_name, object_id } = useParams();
    if (!!app_name && !!model_name && !!object_id && !api_url) {
        api_url = `/api/${app_name}/${model_name}/${object_id}/?depth=1`;
    }
    const { data: objectData, error } = useSWR(() => api_url, fetcher);
    const { data: appHTML } = useSWR(
        () => (api_url ? api_url + "app_full_width_fragment/" : null),
        fetcherHTML
    );
    const ui_url = objectData?.web_url
        ? `${objectData.web_url}?viewconfig=true`
        : null;
    var { data: extraAppConfig } = useSWR(() => ui_url, fetcher);

    const changelog_url = `/api/extras/object-changes/?changed_object_id=${object_id}`;
    const { data: changelogData, changelog_error } = useSWR(
        () => changelog_url,
        fetcher
    );
    const changelog_header_url = `/api/${app_name}/${model_name}/changelog-table-fields/`;
    const { data: changelogTableFields, changelog_table_error } = useSWR(
        () => changelog_header_url,
        fetcher
    );
    const notes_url = `/api/${app_name}/${model_name}/${object_id}/notes/`;
    const { data: noteData, note_error } = useSWR(() => notes_url, fetcher);

    const notes_header_url = `/api/${app_name}/${model_name}/note-table-fields/`;
    // Current fetcher allows to be passed multiple endpoints and fetch them at once
    const { data: noteTableFields, note_table_error } = useSWR(
        () => notes_header_url,
        fetcher
    );
    if (
        error ||
        note_error ||
        changelog_error ||
        note_table_error ||
        changelog_table_error
    ) {
        return (
            <GenericView objectData={objectData}>
                <div>Failed to load {api_url}</div>
            </GenericView>
        );
    }
    // if (!objectData) return <GenericView objectData={objectData} />;

    if (
        !objectData ||
        !noteData ||
        !changelogData ||
        !noteTableFields ||
        !changelogTableFields
    ) {
        return (
            <GenericView>
                <LoadingWidget />
            </GenericView>
        );
    }
    // if (!appConfig) return <GenericView objectData={objectData} />;
    // TODO Right now overloading appConfig to see if Tabs can be dynamically rendered
    extraAppConfig = {
        plugin_tab_1: [
            {
                name: "tab_1_content",
                fields: ["id", "url", "display", "slug", "notes_url"],
                colspan: "3",
                advanced: true,
            },
        ],
        plugin_tab_2: [
            {
                name: "tab_2_content",
                fields: ["id", "url", "display", "slug", "notes_url"],
                colspan: "3",
                advanced: true,
            },
        ],
    };
    const newTabConfig = {
        main: [
            {
                name: model_name,
                fields: Object.keys(objectData),
                colspan: "2",
                rowspan: Object.keys(objectData).length.toString(),
            },
            {
                name: "Extra",
                fields: ["created", "last_updated"],
                colspan: "2",
                rowspan: "2",
            },
            {
                name: "Plugin Table 1",
                fields: ["plugin_attribute_1", "plugin_attribute_2"],
                colspan: "2",
                rowspan: "2",
            },
            {
                name: "Plugin Table 2",
                fields: ["plugin_attribute_3", "plugin_attribute_4"],
                colspan: "2",
                rowspan: "2",
            },
            {
                name: "Plugin Table 3",
                fields: ["plugin_attribute_5", "plugin_attribute_6"],
                colspan: "2",
                rowspan: "2",
            },
        ],
        advanced: [
            {
                name: "Data",
                fields: ["id", "url", "display", "slug", "notes_url"],
                colspan: "3",
                advanced: true,
            },
        ],
        config_context: [
            {
                name: "Config Context",
                fields: ["id", "url", "display", "slug", "notes_url"],
                colspan: "3",
                advanced: true,
            },
        ],
    };
    const appConfig = {
        ...newTabConfig,
        ...extraAppConfig,
    };
    const route_name = `${app_name}:${model_name}`;
    let obj = objectData;
    const default_view = (
        <GenericView>
            <Tabs>
                <Heading>{obj.display}</Heading>
                <br></br>
                <TabList>
                    {Object.keys(appConfig).map((key, idx) => (
                        <Tab>{render_header(key)}</Tab>
                    ))}
                    <Tab>Notes</Tab>
                    <Tab>Change Log</Tab>
                </TabList>
                <TabPanels>
                    {Object.keys(appConfig).map((tab, idx) => (
                        <TabPanel
                            key={tab}
                            eventKey={tab}
                            title={render_header(tab)}
                        >
                            <Card>
                                <CardHeader>
                                    <strong>{render_header(tab)}</strong>
                                </CardHeader>
                                <br></br>
                                <NautobotGrid row={{ count: 5 }}>
                                    {Object.keys(appConfig[tab]).map((item) => (
                                        <NautobotGridItem
                                            colSpan={
                                                appConfig[tab][item].colspan
                                            }
                                            rowSpan={
                                                appConfig[tab][item].rowspan
                                            }
                                        >
                                            <Heading>
                                                {render_header(
                                                    appConfig[tab][item].name
                                                )}
                                            </Heading>
                                            <br />
                                            <TableContainer>
                                                <Table>
                                                    <Tbody>
                                                        {Object.keys(
                                                            appConfig[tab][item]
                                                                .fields
                                                        ).map((key, idx) => (
                                                            <RenderRow
                                                                identifier={
                                                                    appConfig[
                                                                        tab
                                                                    ][item]
                                                                        .fields[
                                                                        key
                                                                    ]
                                                                }
                                                                value={
                                                                    obj[
                                                                        appConfig[
                                                                            tab
                                                                        ][item]
                                                                            .fields[
                                                                            key
                                                                        ]
                                                                    ]
                                                                }
                                                                advanced={
                                                                    appConfig[
                                                                        tab
                                                                    ][item]
                                                                        .advanced
                                                                }
                                                                key={idx}
                                                            />
                                                        ))}
                                                    </Tbody>
                                                </Table>
                                            </TableContainer>
                                        </NautobotGridItem>
                                    ))}
                                </NautobotGrid>
                            </Card>
                        </TabPanel>
                    ))}
                    <TabPanel key="notes" eventKey="notes" title="Notes">
                        <Card>
                            <CardHeader>
                                <strong>Notes</strong>
                            </CardHeader>
                            <ObjectListTableNoButtons
                                tableData={noteData.results}
                                tableHeader={noteTableFields.data}
                                totalCount={noteData.count}
                            ></ObjectListTableNoButtons>
                        </Card>
                    </TabPanel>
                    <TabPanel
                        key="change_log"
                        eventKey="change_log"
                        title="Change Log"
                    >
                        <Card>
                            <CardHeader>
                                <strong>Change Log</strong>
                            </CardHeader>
                            <ObjectListTableNoButtons
                                tableData={changelogData.results}
                                tableHeader={changelogTableFields.data}
                                totalCount={changelogData.count}
                            ></ObjectListTableNoButtons>
                        </Card>
                    </TabPanel>
                </TabPanels>
            </Tabs>
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
