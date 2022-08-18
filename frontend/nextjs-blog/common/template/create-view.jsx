import { Container } from "react-bootstrap"
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Home from "../../pages"
import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import { useState, useEffect } from "react";


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
                                                    <Row key={idx}>
                                                        <Col sm={3}><Form.Label>{field.label}</Form.Label></Col>
                                                        <Col>
                                                            <Form.Group className="mb-3" controlId="formBasicEmail" key={idx}>
                                                                {
                                                                    field.type == "text" ? 
                                                                    <Form.Control type="text" placeholder={field.placeholder}/> 
                                                                    : 
                                                                    field.type == "select" ?
                                                                    <Form.Select aria-label="Default select example">
                                                                        <option>------</option>
                                                                        {
                                                                            field.options.map(item => (
                                                                                <option key={item.value} value={item.value}>{item.label}</option>
                                                                            ))
                                                                        }
                                                                    </Form.Select>
                                                                    :
                                                                    <Form.Control 
                                                                        as="textarea" 
                                                                        placeholder="Leave a comment here"
                                                                        style={{ height: '100px' }}  
                                                                    />  
                                                                }
                                                            </Form.Group>
                                                        </Col>
                                                    </Row>
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
