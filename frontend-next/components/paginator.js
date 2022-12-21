import Pagination from 'react-bootstrap/Pagination';
import Row from "react-bootstrap/Row"
import Col from "react-bootstrap/Col"
import PaginatorForm from './paginator_form';

export default function Paginator({ url, data, page_size, active_page }) {
    let num_pages
    if (data % page_size === 0) {
        num_pages = data / page_size
    } else {
        num_pages = data / page_size + 1
    }
    num_pages = ~~num_pages
    const pages = []
    let offset = page_size
    let limit = page_size
    let original_url = url.split("?")[0]
    let start_range
    let end_range

    if (active_page === num_pages - 1) {
        start_range = (active_page) * page_size + 1
        end_range = data
    } else {
        start_range = (active_page) * page_size + 1
        end_range = (active_page + 1) * page_size
    }

    const num_data = data


    for (let i = 0; i < num_pages; i++) {
        if (i === active_page) {
            pages.push(<Pagination.Item active key={i} href={original_url + `?limit=${limit}&offset=${offset * i}`}>{i + 1}</Pagination.Item>)
        } else {
            pages.push(<Pagination.Item key={i} href={original_url + `?limit=${limit}&offset=${offset * i}`}>{i + 1}</Pagination.Item>)
        }
    }

    return (
        <Row>
            <Col sm={9}>
                <Pagination>
                    <Pagination.First href={original_url + `?limit=${limit}&offset=${offset * 0}`} />
                    {pages}
                    <Pagination.Last href={original_url + `?limit=${limit}&offset=${offset * (num_pages - 1)}`} />
                </Pagination>
            </Col>
            <PaginatorForm list_url={original_url} start={start_range} end={end_range} total_count={num_data}></PaginatorForm>
        </Row>
    );
}

