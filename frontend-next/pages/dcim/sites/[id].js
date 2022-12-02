import Card from "react-bootstrap/Card"
import CardHeader from "react-bootstrap/CardHeader"
import Link from "next/link"
import Tab from "react-bootstrap/Tab"
import Table from "react-bootstrap/Table"
import Tabs from "react-bootstrap/Tabs"
import Layout from "components/layout"
import { useRouter } from "next/router"
import useSWR from "swr"

const fetcher = (url) => fetch(url).then((res) => res.json())

export default function SitesObjectRetrieve() {

  const router = useRouter()
  const { id } = router.query
  const { data: objectData, error } = useSWR(() => "/api/dcim/sites/" + id + "/", fetcher)
  if (error) return <div>Failed to load site</div>
  if (!objectData) return <></>
  return (
    <Layout>
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
                      <Link href={objectData.region.url}>{objectData.region.display}</Link> : "—"}
                  </td>
                </tr>
                <tr>
                  <td>Tenant</td>
                  <td>
                    {objectData.tenant ?
                      <Link href={objectData.tenant.url}>{objectData.tenant.display}</Link> : "—"}
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
        </Tab>
        <Tab eventKey="advanced" title="Advanced">
          <img src="https://raw.githubusercontent.com/nautobot/nautobot/develop/nautobot/docs/nautobot_logo.svg"></img>
        </Tab>
        <Tab eventKey="notes" title="Notes" />
        <Tab eventKey="change_log" title="Change Log" />
      </Tabs>
    </Layout>
  )
}
