import { Col, Row } from "react-bootstrap";
import Pagination from 'react-bootstrap/Pagination';
import PaginatorForm from './paginator_form';


export default function Paginator({ url, data_count, page_size, active_page }) {
  let num_pages
  // Exact page number vs Add one more page for the remainder of the instances
  if (data_count % page_size === 0) {
    num_pages = data_count / page_size
  } else {
    num_pages = data_count / page_size + 1
  }

  // convert float to int
  num_pages = ~~num_pages
  const pages = []

  let list_url = url.split("?")[0] // strip the query parameters to retain the original list url
  let start_range
  let end_range

  if (active_page === num_pages - 1) {
    start_range = (active_page) * page_size + 1
    end_range = data_count
  } else {
    start_range = (active_page) * page_size + 1
    end_range = (active_page + 1) * page_size
  }

  for (let i = 0; i < num_pages; i++) {
    if (i === active_page) {
      pages.push(<Pagination.Item active key={i} href={list_url + `?limit=${page_size}&offset=${page_size * i}`}>{i + 1}</Pagination.Item>)
    } else {
      pages.push(<Pagination.Item key={i} href={list_url + `?limit=${page_size}&offset=${page_size * i}`}>{i + 1}</Pagination.Item>)
    }
  }

  return (
    <Row>
      <Col sm={9}>
        <Pagination>
          <Pagination.First href={list_url + `?limit=${page_size}&offset=${page_size * 0}`} />
          {pages}
          <Pagination.Last href={list_url + `?limit=${page_size}&offset=${page_size * (num_pages - 1)}`} />
        </Pagination>
      </Col>
      <PaginatorForm start={start_range} end={end_range} total_count={data_count}></PaginatorForm>
    </Row>
  );
}
