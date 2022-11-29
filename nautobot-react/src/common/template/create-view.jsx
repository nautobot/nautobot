import { Container } from "react-bootstrap"
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import App from "../../App"
import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import { useState, useEffect } from "react";
import NautobotInput from "../components/nautobot-default-input"
import { axios_instance } from "../utils/utils";


export default function CreateViewTemplate({ children }, props) {
    const [pageConfig, setPageConfig] = useState(
        {
            "form_fields": require("../../common/utils/api/sites/add-form-fields.json"),
        }
    )
    const [formFields, setFormFields] = useState({})

    useEffect(async () => {
        const form_fields_url = location.pathname.replace("add", "") + "form-fields/"
        const formFields = await axios_instance.get(form_fields_url)
        setFormFields(formFields.data)
    }, [])

    return (
        <App>
            <Container>
                <Row className="justify-content-md-center">
                    <Col xs lg="7">
                        {
                            !children ?
                                <>
                                    <h4>Add New</h4>
                                    {
                                        Object.entries(formFields).map((group, idx) => (
                                            <Card className="mb-4" key={idx}>
                                                <Card.Header><b>{group[0]}</b></Card.Header>
                                                <Card.Body>
                                                    {
                                                        group[1].map((field, idx) => (
                                                            field ?
                                                                ["char-field", "integer-field", "others"].includes(field.type) ?
                                                                    <NautobotInput key={idx} _type="text" label={field.label} />
                                                                    :
                                                                    field.type == "dynamic-choice-field" ?
                                                                        <NautobotInput
                                                                            key={idx}
                                                                            _type="select"
                                                                            label={field.label}
                                                                            options={field.choices}
                                                                        />
                                                                        :
                                                                        <NautobotInput key={idx} _type="checkbox" label="" />
                                                                :
                                                                <></>
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

        </App>
    )
}
