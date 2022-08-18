
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Button from 'react-bootstrap/Button';
import * as Icon from 'react-feather';
import NautobotTable from "../../common/components/table"
import NautobotFilterForm from "../../common/components/filter-form";
import { useState, useEffect } from "react";
import Home from '../../pages';
import { NavLink } from 'react-bootstrap';
import { useRouter } from 'next/router';

export default function ListView(props){
    const router = useRouter()
    const [pageConfig, setPageConfig] = useState(
        {
            "buttons": {
                "configure": {
                    "label": "Configure",
                    "icon": <Icon.Settings size={15} />,
                    "color": "outline-dark"
                },
                "add": {
                    "label": "Add",
                    "icon": <Icon.Plus size={15} />,
                    "color": "primary",
                    "link": "add",
                },
                "import": {
                    "label": "Import",
                    "icon": <Icon.Cloud size={15} />,
                    "color": "info",
                    "link": "import",
                },
                "export": {
                    "label": "Export",
                    "icon": <Icon.Database size={15} />,
                    "color": "success",
                },
            },
            "data": require("../../common/utils/table_api.json"),
            "filter_form": require("../../common/utils/table_api.json")["filter_form"],
        }
    )

    useEffect(() => {
        // setTableData(props.list_url ? props.list_url : tableDataAPI)
        if (props.config) {
            if (props.config.buttons) {
                
            }
        }

    }, [pageConfig])

    return (
        <Home>
            <Row>
                <Col xs={8}>
                    <h3>{pageConfig.data.title}</h3>
                </Col>
                <Col style={{textAlign: "right"}} className="action-items-container">
                    {
                        Object.entries(pageConfig.buttons).map((item, idx) => (
                            <NavLink key={idx} href={item[1].link ?  router.pathname + "/" + item[1].link : "#"}>
                                <Button 
                                    key={idx} 
                                    size="sm" 
                                    variant={item[1].color}
                                    className='mr-2 action-btn'
                                >
                                    {item[1].icon} {item[1].label} 
                                </Button>
                            </NavLink>
                        ))
                    }
                </Col>
            </Row>
            <Row>
                <Col xs={9}>
                    <NautobotTable 
                        data={
                            pageConfig.data ? 
                                pageConfig.data.data ?
                                    pageConfig.data.data
                                    :
                                    {}
                                :
                                {}
                        } 
                        header={
                            pageConfig.data ? 
                                pageConfig.data.header ?
                                    pageConfig.data.header
                                    :
                                    []
                                :
                                []
                        } 
                    />
                </Col>
                <Col>
                    <NautobotFilterForm 
                        fields={
                            pageConfig.filter_form ? 
                                pageConfig.filter_form
                                :
                                []
                        }
                    />
                </Col>
            </Row>
        </Home>
    )
}