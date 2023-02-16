import { Button, ButtonGroup, Col, Container, Row } from "react-bootstrap"
import * as Icon from "react-icons/tb"
import { useLocation, useSearchParams } from "react-router-dom"
import useSWR from "swr"

import NautobotTable from "@components/core/BSTable"
import Paginator from "@components/common/paginator"


const fetcher = (...urls) => {
  const f = url => fetch(url, { credentials: "include" }).then(r => r.json())
  return Promise.all(urls.map(url => f(url)))
}

export default function BSListViewTemplate({ list_url }) {
  const headers_url = list_url + "table-fields/"
  let location = useLocation();
  let searchParams = useSearchParams()[0];


  // Default page size and active page number
  let size = 50
  let active_page_number = 0

  if (searchParams.get("limit")) {
    list_url += `?limit=${searchParams.get("limit")}`
    size = searchParams.get("limit")
  }
  if (searchParams.get("offset")) {
    list_url += `&offset=${searchParams.get("offset")}`
    active_page_number = searchParams.get("offset") / size
  }

  const urls = [list_url, headers_url]
  const { data, error } = useSWR(urls, fetcher)

  if (error) return <div>Failed to load {list_url}</div>
  if (!data) return <></>

  const tableData = data[0].formData.results
  const tableHeader = data[1].formData.data
  const dataCount = data[0].formData.count
  return (
    <Container>
      <Row>
        <Col>
          <ButtonGroup>
            <Button href={`${location.pathname}add`}><Icon.TbPlus /> Add</Button>{' '}
            <Button variant="info"><Icon.TbDatabaseImport /> Import</Button>{' '}
            <Button variant="success"><Icon.TbDatabaseExport /> Export</Button>{' '}
          </ButtonGroup>
        </Col>
      </Row>
      <Row>
        <Col>
          <NautobotTable data={tableData} headers={tableHeader} />
        </Col>
      </Row>
      <Row>
        <Col>
          <Paginator url={location.pathname} data_count={dataCount} page_size={size} active_page={active_page_number}></Paginator>
        </Col>
      </Row>
    </Container>
  );
}
