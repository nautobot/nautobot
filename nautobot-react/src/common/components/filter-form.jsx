import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import InputGroup from 'react-bootstrap/InputGroup';
import * as Icon from 'react-feather';


export default function NautobotFilterForm(props){
    return (
        <Card>
            <Card.Header><b>Search</b></Card.Header>
            <Card.Body>
            <InputGroup className="mb-3">
                <Form.Control placeholder="Search" />
                <InputGroup.Text id="basic-addon2" ><Icon.Search size={15} /></InputGroup.Text>
            </InputGroup>
            {
                props.fields.map((field, idx) => (
                    <Form.Group className="mb-3" controlId="formBasicEmail" key={idx}>
                        <Form.Label>{field.label}</Form.Label>
                        {
                            field.type == "text" ? 
                            <Form.Control type="email" placeholder={field.placeholder}/> 
                            : 
                            <Form.Select aria-label="Default select example">
                                <option>------</option>
                                {
                                    field.options.map(item => (
                                        <option key={item.value} value={item.value}>{item.label}</option>
                                    ))
                                }
                            </Form.Select>
                        }
                    </Form.Group>
                ))
            }
                <Button size="sm" variant="success"><Icon.Check size={15} /> Apply</Button> {' '}
                <Button size="sm" variant="outline-dark"><Icon.Download size={15} /> Clear</Button>
            </Card.Body>
        </Card>
    )
}