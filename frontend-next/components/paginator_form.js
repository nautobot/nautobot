import React, { useState } from "react";
import Form from 'react-bootstrap/Form';
import Col from "react-bootstrap/Col"
import { useRouter } from "next/router"


export default function PaginatorForm({ list_url, start, end, total_count }) {
    const router = useRouter()
    let paginator_string = `Showing ${start} - ${end} of ${total_count}`
    const [type, setType] = useState("PaginatorForm");
    return (
        <Col sm={3}>
            <Form.Control
                as="select"
                value={router.query.limit}
                onChange={e => {
                    setType(e.target.value);
                    router.push({
                        query: { appname: router.query.appname, pagename: router.query.pagename, limit: e.target.value, offset: 0 },
                    })
                }}
            >
                <option>50</option>
                <option>100</option>
                <option>200</option>
                <option>500</option>
            </Form.Control>
            <Form.Text muted>
                {paginator_string}
            </Form.Text>
        </Col >
    )
}
