import Card from "react-bootstrap/Card"
import CardHeader from "react-bootstrap/CardHeader"
import { Link } from "react-router-dom";
import { nautobot_url } from "../index"
import Tab from "react-bootstrap/Tab"
import Table from "react-bootstrap/Table"
import Tabs from "react-bootstrap/Tabs"
import { useParams } from "react-router-dom"
import useSWR from "swr"

const fetcher = (url) => fetch(url, { credentials: "include" }).then((res) => res.ok ? res.json() : null)
const fetcherHTML = (url) => fetch(url, { credentials: "include" }).then((res) => res.ok ? res.text() : null)

export default function ObjectRetrieve({ api_url }) {

  const { app_name, model_name, object_id } = useParams()
  if (!!app_name && !!model_name && !!object_id && !api_url) {
    api_url = `${nautobot_url}/api/${app_name}/${model_name}/${object_id}/`
  }
  const { data: objectData, error } = useSWR(() => api_url, fetcher)
  const { data: pluginHTML, _ } = useSWR(() => api_url ? api_url + "plugin_full_width_fragment/" : null, fetcherHTML)
  if (error) return <div>Failed to load {api_url}</div>
  if (!objectData) return <></>
  return (
    <>
        <h1>{objectData.name}</h1>
        <p>
            <small className="text-muted">
            {objectData.created &&
                <>Created {objectData.created} &middot; </>
            }
            <> Updated <span title={objectData.last_updated}>xyz seconds</span> ago</>
            </small>
        </p>
        <div className="pull-right noprint"></div>
        <Tabs defaultActiveKey="site">
            <Tab eventKey="site" title="Site">
            <br />
            <Card>
                <CardHeader>
                <strong>Site</strong>
                </CardHeader>
                <Table hover>
                <tbody>
                    <tr>
                    <td>Status</td>
                    <td>
                        <span className="label">
                        {objectData.status ? <>{objectData.status.label}</> : "—"}
                        </span>
                    </td>
                    </tr>
                    <tr>
                    <td>Region</td>
                    <td>
                        {objectData.region ?
                        <Link to={objectData.region.url}>{objectData.region.display}</Link> : "—"}
                    </td>
                    </tr>
                    <tr>
                    <td>Tenant</td>
                    <td>
                        {objectData.tenant ?
                        <Link to={objectData.tenant.url}>{objectData.tenant.display}</Link> : "—"}
                    </td>
                    </tr>
                    <tr>
                    <td>Facility</td>
                    <td>
                        {objectData.facility ? <>{objectData.facility}</> : "—"}
                    </td>
                    </tr>
                    <tr>
                    <td>AS Number</td>
                    <td>
                        {objectData.asn ? <>{objectData.asn}</> : "—"}
                    </td>
                    </tr>
                    <tr>
                    <td>Time Zone</td>
                    <td>
                        {objectData.time_zone ? <>{objectData.time_zone}</> : "—"}
                    </td>
                    </tr>
                    <tr>
                    <td>Description</td>
                    <td>
                        {objectData.description ? <>{objectData.description}</> : "—"}
                    </td>
                    </tr>
                </tbody>
                </Table>
            </Card>
            <br />
            <div dangerouslySetInnerHTML={{ __html: pluginHTML }} />
            <br />
            </Tab>
            <Tab eventKey="advanced" title="Advanced">
            <br />
            </Tab>
            <Tab eventKey="notes" title="Notes" />
            <Tab eventKey="change_log" title="Change Log">
            <br />
            <div dangerouslySetInnerHTML={{ __html: "<p>Your html code here.<p>" }} />
            </Tab>
        </Tabs>
    </>
  )
}
