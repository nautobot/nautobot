import { Button, Card, CardHeader, SkeletonText } from "@chakra-ui/react"; // TODO: use nautobot-ui when available
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
    Thead,
    Th,
    Tag,
    TagLabel,
} from "@nautobot/nautobot-ui";
import { ReferenceDataTag } from "@components/ReferenceDataTag";
import { useLocation, useParams } from "react-router-dom";
import useSWR from "swr";
import { useRef } from "react";
// import AppFullWidthComponentsWithProps from "@components/AppFullWidthComponents";
import AppComponents from "@components/Apps";
import { toTitleCase } from "@utils/string";
import GenericView from "@views/generic/GenericView";
import ObjectListTable from "@components/ObjectListTable";
import { useGetRESTAPIQuery } from "@utils/api";
import { humanFriendlyDate } from "@utils/date";
import { uiUrl } from "@utils/url";
import axios from "axios";
import TableItem from "@components/TableItem";

const fetcher = (url) =>
    fetch(url, { credentials: "include" }).then((res) =>
        res.ok ? res.json() : null
    );
const optionFetcher = (url) => axios.options(url, { withCredentials: true }).then((res) => res.data);

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

// Make this a global component for all Title with NautobotTitleIcon; revise the fontSize
function TitleWithNautobotIcon({as, title}){
    return (
        <Heading as={as} display="flex" gap="5px" alignItems="center" fontSize={"medium"} mb="2">
            <NtcThumbnailIcon width="25px" height="30px" />{" "} {title}
        </Heading>
    )
}

function RenderFieldValue({value, link, color}){
    let field_value = value;
    
    if (color) {
        field_value = (
            <Button size="xs" px="3">
                {value}
            </Button>
        )
    }
    if (link){
        field_value = <Link to="">{field_value}</Link>
    }
    return field_value
}

function RenderList({fields, template_actions, ...props}) {
    return (
        <TableContainer>
            <Table>
                <Tbody>
                    {
                        fields.map((field, i) => {
                            // TODO: create/get a util function that converts {app_name, model, id} to url path
                            let link_path = field.link ? "/" : null;
                            let field_data = {...field, label: field.value};
                            if(!field.link && !field.color){
                                field_data = field.value;
                            }
                            return (
                                <Tr>
                                    <Td>{field.label}</Td>
                                    <Td><TableItem obj={field_data} url={link_path} /></Td>
                                </Tr>
                            )
                        })
                    }
                </Tbody>
            </Table>
        </TableContainer>
    )
}

function RenderFullBox({field}) {
    return (
        <TableContainer>
            <Table>
                <Tbody>
                    <Tr>
                        <Td>

                            {/* TEXT IS NOT BREAKING {field} */}
                        </Td>
                    </Tr>
                </Tbody>
            </Table>
        </TableContainer>
    )
}

function RenderTable(props) {
    return <>TABLE</>
}

function RenderRowV2({title, data, ...props}){
    return (
        <Card mb="5" border={1}>
            <TitleWithNautobotIcon title={title} as="h3" />
            {
                data.template === "list" ? 
                    <RenderList {...data} />
                : 
                data.template === "table" ?
                    <RenderTable {...data} />
                :
                    <RenderFullBox {...data} />
            }
        </Card>
    )
}


function RenderColumn({data, colSpan, ...props}){
    return (
        <NautobotGridItem colSpan={colSpan} {...props}>
            {
                Object.entries(data.groups).map(([group_title, group_data], idx) => {
                    return <RenderRowV2 title={group_title} data={group_data} {...props} key={idx} />;
                })
            }
        </NautobotGridItem>

    )
}

function RenderDefaultView({obj, appConfig, schemaData}) {
    const { detail_view_schema: schema } = schemaData
    return (
        <GenericView objectData={obj}>
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
                        <TabPanel key={1}>
                            <Card>
                                <NautobotGrid columns={schema.column_no}>
                                    {
                                        // for some reason NautobotGrid columns is always 4 regardless of what value you pass
                                        // For that reason we would need to calculate the colSpan for each column
                                        // colSpan = 4 / no of col # Should be floor
                                        Array.from({length: schema.column_no}, (_, i) => i+1).map((col_no, idx) => {
                                            const colSpan = Math.floor(4 / parseInt(schema.column_no))
                                            return (
                                            <RenderColumn key={idx} colSpan={colSpan} data={schema.columns[col_no]} />
                                        )})
                                    }
                                    
                                </NautobotGrid>
                            </Card>
                        </TabPanel>
                    </TabPanels>
                </Tabs>
            </Box>
            
        </GenericView>
    )
}


// TODO: Extract into a standalone component
function RenderLoadingScreen(){
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
    )
}

// TODO: Move to utils.js
function removeURLParameter(url, parameter) {
    const url_parts = url.split('?');   
    if (url_parts.length >= 2) {
        const prefix = encodeURIComponent(parameter) + '=';
        const pars = url_parts[1].split(/[&;]/g);
        for (let i = pars.length; i-- > 0;) {    
            if (pars[i].lastIndexOf(prefix, 0) !== -1) {  
                pars.splice(i, 1);
            }
        }
        return url_parts[0] + (pars.length > 0 ? '?' + pars.join('&') : '');
    }
    return url;
}


export default function ObjectRetrieve({ api_url }) {
    const { app_name, model_name, object_id } = useParams();
    const location = useLocation();
    const isPluginView = location.pathname.includes("/plugins/");
    const pluginPrefix = isPluginView ? "plugins/" : "";
    if (!!app_name && !!model_name && !!object_id && !api_url) {
        api_url = `/api/${pluginPrefix}${app_name}/${model_name}/${object_id}/?depth=1`;
    }
    
    const { data: objectData, isError: error } = useSWR(() => api_url, fetcher);
    const ui_url = objectData?.url ? `${objectData.url}detail-view-config/` : null;
    const { data: appConfig, isError: appConfigError } = useSWR(() => ui_url, fetcher);
    // Options do not work with query params; Hence removal of query params
    const optionsUrl = removeURLParameter(api_url, "depth")
    const { data: schemaData, isError: schemaError } = useSWR(() => optionsUrl, optionFetcher);

    // If Possible move appconfig over to schema, maybe appConfigSchema
    if (error || appConfigError || schemaError) {
        return (
            <GenericView>
                <div>Failed to load {api_url}</div>
            </GenericView>
        )
    }
    else if (objectData && appConfig && schemaData){
        return <RenderDefaultView obj={objectData} appConfig={appConfig} schemaData={schemaData} />
    }
    return <RenderLoadingScreen />;
}
