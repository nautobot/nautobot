import Card from "react-bootstrap/Card"
import CardHeader from "react-bootstrap/CardHeader"
import { nautobot_url } from "../../index"
import Tab from "react-bootstrap/Tab"
import Table from "react-bootstrap/Table"
import Tabs from "react-bootstrap/Tabs"
import { useParams } from "react-router-dom"
import useSWR from "swr"

import create_plugin_tab from "@components/plugins/PluginTab"

const fetcher = (url) => fetch(url, { credentials: "include" }).then((res) => res.ok ? res.json() : null)
const fetcherHTML = (url) => fetch(url, { credentials: "include" }).then((res) => res.ok ? res.text() : null)
const fetcherTabs = (url) => fetch(url, { credentials: "include" }).then((res) => {
  return res.json().then((data) => {
    // console.log(data)

    let tabs = []
    data.tabs.map((tab_top) => {
      Object.keys(tab_top).map(function (tab_key) {
        let tab = tab_top[tab_key]
        let tab_component = create_plugin_tab({tab: tab})
        tabs.push(tab_component)
      })
    })
    return tabs
  })
})

function RenderRow(props) {
  var key = props.identifier;
  var value = props.value;

  if (["id", "url", "display", "slug", "notes_url"].includes(key) ^ !props.advanced) {
    return null;
  }

  // "foo_bar" --> "Foo Bar"
  key = key.split("_").map((x) => (x[0].toUpperCase() + x.slice(1))).join(" ");

  return (
    <tr>
      <td>{key}</td>
      <td>{
        value === null || value === "" ?
          "—" :
          Array.isArray(value) ?
            <ul class="list-unstyled">{value.map((item) =>
              typeof (item) == "object" ? <li>{item["display"]}</li> : <li>{item}</li>
            )}</ul> :
            typeof (value) == "object" ?
              value["display"] :
              typeof (value) == "array" ?
                value.join(", ") :
                typeof (value) == "boolean" ?
                  value ? "✅" : "🚫" :
                  value
      }</td>
    </tr>
  );
}

export default function ObjectRetrieve({ api_url }) {
  var pluginConfig = []
  const { app_name, model_name, object_id } = useParams()
  if (!!app_name && !!model_name && !!object_id && !api_url) {
    api_url = `${nautobot_url}/api/${app_name}/${model_name}/${object_id}/`
  }
  const { data: objectData, error } = useSWR(() => api_url, fetcher)
  const { data: pluginHTML } = useSWR(() => api_url ? api_url + "plugin_full_width_fragment/" : null, fetcherHTML)
  const ui_url = objectData ? `${nautobot_url}${objectData.web_url}?viewconfig=true` : null
  var { data: pluginConfig } = useSWR(() => ui_url , fetcherTabs)
  if (error) return <div>Failed to load {api_url}</div>
  if (!objectData) return <></>
  if (!pluginConfig) return <></>
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
      <Tabs defaultActiveKey="main" mountOnEnter="true">
        <Tab eventKey="main" title="Main">
          <br />
          <Card>
            <CardHeader>
              <strong>Main</strong>
            </CardHeader>
            <Table hover>
              <tbody>
                {Object.keys(objectData).map((key) => <RenderRow identifier={key} value={objectData[key]} advanced />)}
              </tbody>
            </Table>
          </Card>
          <br />
          <div dangerouslySetInnerHTML={{ __html: pluginHTML }} />
          <br />
        </Tab>
        <Tab eventKey="advanced" title="Advanced">
          <br />
          <Card>
            <CardHeader>
              <strong>Advanced</strong>
            </CardHeader>
            <Table hover>
              <tbody>
                {Object.keys(objectData).map((key) => <RenderRow identifier={key} value={objectData[key]} advanced={false} />)}
              </tbody>
            </Table>
          </Card>
        </Tab>
        <Tab eventKey="notes" title="Notes" />
        <Tab eventKey="change_log" title="Change Log">
          <br />
          <div dangerouslySetInnerHTML={{ __html: "<p>Your html code here.<p>" }} />
        </Tab>
        {pluginConfig}
      </Tabs>
    </>
  )
}
