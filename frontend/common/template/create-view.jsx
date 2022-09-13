import { Container } from "react-bootstrap"
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Home from "../../pages"
import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import { useState, useEffect } from "react";
import NautobotInput from "../../common/components/nautobot-default-input"


export default function CreateViewTemplate({children}, props){
    const [pageConfig, setPageConfig] = useState(
        {
            "form_fields": require("../../common/utils/api/sites/add-form-fields.json"),
        }
    )

    useEffect(() => {
        // setTableData(props.list_url ? props.list_url : tableDataAPI)
        // if () {
        //     if (props.config.buttons) {
        //         console.log()
        //     }
        // }

    }, [pageConfig])

    return (
        <Home>
            <Container>
            <Row className="justify-content-md-center">
                <Col xs lg="7">
                    {
                        !children ?
                        <>
                            <h4>Add a new site</h4>
                            {
                                pageConfig.form_fields.map((item, idx) => (
                                    <Card className="mb-4" key={idx}>
                                        <Card.Header><b>{item.title}</b></Card.Header>
                                        <Card.Body>
                                            {
                                                item.fields.map((field, idx) => (
                                                    field.type == "text" ? 
                                                    <NautobotInput _type="text" label={field.label} />
                                                    :
                                                    field.type == "select" ? 
                                                    <NautobotInput _type="select" label={field.label} options={field.options} />
                                                    :
                                                    <NautobotInput _type="checkbox" label={field.label} />
                                                ))
                                            }
                                        </Card.Body>
                                    </Card>
                                ))
                            }
                        </>
                        :
                        children
                    }
                    
                    

                    <Button variant="primary">Create</Button> {' '}
                    <Button variant="primary">Create and Add New</Button> {' '}
                    <Button variant="outline-dark">Cancel</Button>
                </Col>
            </Row>
                
            </Container>
            
        </Home>
    )
}
