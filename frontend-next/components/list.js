import Col from "react-bootstrap/Col"
import NautobotTable from "./table"
import Paginator from "./paginator"
import Row from "react-bootstrap/Row"
import useSWR from "swr"
import { useRouter } from "next/router"
import { Container } from "react-bootstrap"

const fetcher = (...urls) => {
  const f = url => fetch(url, { credentials: "include" }).then(r => r.json())
  return Promise.all(urls.map(url => f(url)))
}

export default function ListViewTemplate({ list_url }) {
  const router = useRouter()
  const headers_url = list_url + "table-fields/"

  // Default page size and active page number
  let size = 50
  let active_page_number = 0

  if (router.query.limit) {
    list_url += `?limit=${router.query.limit}`
    size = router.query.limit
  }
  if (router.query.offset) {
    list_url += `&offset=${router.query.offset}`
    active_page_number = router.query.offset / size
  }

  const urls = [list_url, headers_url]
  const { data, error } = useSWR(urls, fetcher)

  if (error) return <div>Failed to load {list_url}</div>
  if (!data) return <></>

  const tableData = data[0].results
  const tableHeader = data[1].data
  const dataCount = data[0].count

  return (
    <Container>
      <Row>
        <Col>
          <NautobotTable data={tableData} headers={tableHeader} />
        </Col>
      </Row >
      <Row>
        <Col>
          <Paginator url={router.asPath} data_count={dataCount} page_size={size} active_page={active_page_number}></Paginator>
        </Col>
      </Row>
    </Container>
  );
}
