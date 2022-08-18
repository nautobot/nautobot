import CreateViewTemplate from "../../../common/template/create-view"
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';

export default function ExamplePluginAdd(){
    return (
        <CreateViewTemplate>
            <h4>Add a new example plugin model</h4>
            <Card className="mb-4">
                <Card.Header><b>Example Custom Form</b></Card.Header>
                <Card.Body>
                    <Row>
                        <Col sm={3}><Form.Label>Item 1</Form.Label></Col>
                        <Col>
                            <Form.Group className="mb-3" controlId="formBasicEmail">
                                <Form.Control type="text" placeholder="Item 1" />
                            </Form.Group>
                        </Col>
                    </Row>
                    <Row>
                        <Col sm={3}><Form.Label>Item 2</Form.Label></Col>
                        <Col>
                            <Form.Group className="mb-3" controlId="formBasicEmail">
                                <Form.Control type="text" placeholder="Item 2" />
                            </Form.Group>
                        </Col>
                    </Row>
                </Card.Body>
            </Card>

        </CreateViewTemplate>
    )
}