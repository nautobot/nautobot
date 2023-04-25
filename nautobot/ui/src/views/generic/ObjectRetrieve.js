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
    Tbody,
    Td,
    Tr,
} from "@nautobot/nautobot-ui";
import { useParams } from "react-router-dom";
import useSWR from "swr";
import { useRef } from "react";
import AppFullWidthComponentsWithProps from "@components/apps/AppFullWidthComponents";
import create_app_tab from "@components/apps/AppTab";
import AppComponents from "@components/core/Apps";
import { LoadingWidget } from "@components/common/LoadingWidget";
import GenericView from "@views/generic/GenericView";
import ObjectListTableNoButtons from "@components/common/ObjectListTableNoButtons";

const fetcher = (url) =>
    fetch(url, { credentials: "include" }).then((res) =>
        res.ok ? res.json() : null
    );
const fetcherHTML = (url) =>
    fetch(url, { credentials: "include" }).then((res) =>
        res.ok ? res.text() : null
    );
const fetcherTabs = (url) =>
    fetch(url, { credentials: "include" }).then((res) => {
        return res.json().then((data) => {
            let tabs = data.tabs.map((tab_top) =>
                Object.keys(tab_top).map(function (tab_key) {
                    let tab = tab_top[tab_key];
                    let tab_component = create_app_tab({ tab: tab });
                    return tab_component;
                })
            );
            return tabs;
        });
    });

function Render_value(value) {
    const ref = useRef();
    switch (typeof value) {
        case "object":
            return value === null ? (
                <FontAwesomeIcon icon={faMinus} />
            ) : Array.isArray(value) ? (
                value.map((v) => (
                    <div>
                        <Link ref={ref} href={v["web_url"]}>
                            {v["display"]}
                        </Link>
                    </div>
                ))
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
    const ui_url = objectData?.formData
        ? `${objectData.formData.web_url}?viewconfig=true`
        : null;
    var { data: appConfig } = useSWR(() => ui_url, fetcherTabs);

    const changelog_url = `/api/extras/object-changes/?changed_object_id=${object_id}`
    const { data: changelogData, changelog_error } = useSWR(() => changelog_url, fetcher);
    const changelog_header_url = `/api/${app_name}/${model_name}/changelog-table-fields/`
    const { data: changelogTableFields, changelog_table_error } = useSWR(() => changelog_header_url, fetcher);
    const notes_url = `/api/${app_name}/${model_name}/${object_id}/notes/`
    const { data: noteData, note_error } = useSWR(() => notes_url, fetcher);

    const notes_header_url = `/api/${app_name}/${model_name}/note-table-fields/`
    // Current fetcher allows to be passed multiple endpoints and fetch them at once
    const { data: noteTableFields, note_table_error } = useSWR(() => notes_header_url, fetcher);
    if (error || note_error || changelog_error || note_table_error || changelog_table_error) {
        return (
            <GenericView objectData={objectData}>
                <div>Failed to load {api_url}</div>
            </GenericView>
        );
    }
    // if (!objectData) return <GenericView objectData={objectData} />;

    if (!objectData || !noteData || !noteTableFields || !changelogTableFields) {
        return (
            <GenericView>
                <LoadingWidget />
            </GenericView>
        );
    }
    // if (!appConfig) return <GenericView objectData={objectData} />;
    // TODO Right now overloading appConfig to see if Tabs can be dynamically rendered
    appConfig = {
        main: "main page",
        advanced: "advanced attributes",
        note: "object notes",
        change_log: "object changes",
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
                        <Tab>{key.charAt(0).toUpperCase() + key.slice(1)}</Tab>
                    ))}
                </TabList>
                <TabPanels>
                    <TabPanel key="main" eventKey="main" title="Main">
                        <br />
                        <Card>
                            <CardHeader>
                                <strong>Main</strong>
                            </CardHeader>
                            <Table>
                                <Tbody>
                                    {Object.keys(obj).map((key, idx) => (
                                        <RenderRow
                                            identifier={key}
                                            value={obj[key]}
                                            advanced={false}
                                            key={idx}
                                        />
                                    ))}
                                </Tbody>
                            </Table>
                        </Card>
                        <br />
                        <div dangerouslySetInnerHTML={{ __html: appHTML }} />
                        <br />
                        {AppFullWidthComponentsWithProps(route_name, obj)}
                    </TabPanel>
                    <TabPanel
                        key="advanced"
                        eventKey="advanced"
                        title="Advanced"
                    >
                        <br />
                        <Card>
                            <CardHeader>
                                <strong>Advanced</strong>
                            </CardHeader>
                            <Table>
                                <Tbody>
                                    {Object.keys(obj).map((key, idx) => (
                                        <RenderRow
                                            identifier={key}
                                            value={obj[key]}
                                            advanced
                                            key={idx}
                                        />
                                    ))}
                                </Tbody>
                            </Table>
                        </Card>
                    </TabPanel>
                    <TabPanel key="notes" eventKey="notes" title="Notes">
                        <Card>
                            <CardHeader>
                                <strong>Notes</strong>
                            </CardHeader>
                            <ObjectListTableNoButtons
                                tableData={noteData.results}
                                tableHeader={noteTableFields.data}
                                totalCount={noteData.count}
                            >
                            </ObjectListTableNoButtons>
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
                            >
                            </ObjectListTableNoButtons>
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
