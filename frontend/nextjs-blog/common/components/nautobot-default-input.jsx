import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';

export default function NautobotInput(props){
    return (
        <Row>
            {
                props._type == "text" || props._type == "select" ?
                <>
                    <Col sm={3}><Form.Label>{props.label}</Form.Label></Col>
                    <Col>
                        <Form.Group className="mb-3" controlId="formBasicEmail">
                            {
                                props._type == "text" ?
                                <Form.Control type="text" placeholder={props.placeholder || props.label} />
                                :
                                <Form.Select aria-label="Default select example">
                                    <option>------</option>
                                    {
                                        props.options.map(item => (
                                            <option key={item.value} value={item.value}>{item.label}</option>
                                        ))
                                    }
                                </Form.Select>
                            }
                            
                        </Form.Group>
                    </Col>
                </>
                :
                <Form.Control 
                    as="textarea" 
                    placeholder={props.placeholder || props.label}
                    style={{ height: '100px' }}  
                /> 
            }
            
        </Row>
    )
}
