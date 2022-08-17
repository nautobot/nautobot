
import Alert from 'react-bootstrap/Alert';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Button from 'react-bootstrap/Button';
import * as Icon from 'react-feather';
import NautobotTable from "../../common/components/table"
import NautobotFilterForm from "../../common/components/filter-form";
import { useState, useEffect } from "react";
import Home from '../../pages';

export default function ListView(props){
    const [tableData, setTableData] = useState({header: [], data: [], filter_form: []})

    useEffect(() => {
        const tableDataAPI = require("../../common/utils/table_api.json")
        setTableData(props.list_url ? props.list_url : tableDataAPI)

    }, [tableData])

    return (
        <Home>
            <Alert variant="success" style={{textAlign: "center"}}>
                Example Plugin says “Hello, admin!” 👋 <br />
                You are viewing a table of sites
            </Alert>
            
            <Row>
                <Col xs={8}>
                    <h3>{tableData.title}</h3>
                </Col>
                <Col style={{textAlign: "right"}}>
                    <Button size="sm" variant="outline-dark"><Icon.Settings size={15} /> Configure</Button>{' '}
                    <Button size="sm" variant="primary"><Icon.Plus size={15} /> Add</Button>{' '}
                    <Button size="sm" variant="info"><Icon.Inbox size={15} /> Import</Button>{' '}
                    <Button size="sm" variant="success"><Icon.Database size={15} /> Export</Button>
                </Col>
            </Row>
            <Row>
                <Col xs={9}>
                    <NautobotTable data={tableData.data} header={tableData.header} />
                </Col>
                <Col>
                    <NautobotFilterForm fields={tableData.filter_form} />
                </Col>
            </Row>
        </Home>
    )
}