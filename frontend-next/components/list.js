import Col from "react-bootstrap/Col"
import Layout from "./layout"
import NautobotTable from "./table"
import Row from "react-bootstrap/Row"
import useSWR from "swr"

const fetcher = (...urls) => {
  const f = url => fetch(url, { credentials: "include" }).then(r => r.json())
  return Promise.all(urls.map(url => f(url)))
}

export default function ListViewTemplate({ list_url }) {

  const urls = [list_url, list_url + "table-fields/"]
  const { data, error } = useSWR(urls, fetcher)
  if (error) return <div>Failed to load {list_url}</div>
  if (!data) return <></>

  const tableData = data[0].results
  const tableHeader = data[1].data
  return (
    <div>
      <Layout>
        <Row>
          <Col>
            <NautobotTable data={tableData} headers={tableHeader} />
          </Col>
        </Row>
      </Layout>
    </div>
  );
}
