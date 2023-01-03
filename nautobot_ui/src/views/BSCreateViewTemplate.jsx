import axios from "axios"
import { Button, Col, Card, Row } from "react-bootstrap"
import Cookies from 'js-cookie'
import { useState } from "react"
import { RJSFSchema } from "@rjsf/utils";
import validator from "@rjsf/validator-ajv8";
import Form from "@rjsf/core";
import useSWR from "swr"


const csrf_token = Cookies.get('csrftoken');

const fetcher = url => axios.get(url + "create/", {withCredentials: true}).then(res => res.data)

export default function BSCreateViewTemplate({ list_url }) {
  const [formData, setFormData] = useState(null)
  const { data, error } = useSWR(list_url, fetcher)

  if (error) return <div>Failed to load schema from {list_url}</div>
  if (!data) return <></>

  const post_schema = data.serializer.schema
  const ui_schema = data.serializer.uiSchema
  const log = (type) => console.log.bind(console, type)
  const model_name_title = post_schema.title
  const model_name = model_name_title.toLowerCase()

  // Using axios so that we can do a POST.
  const onSubmit = ({formData}) => axios({
    method: "post",
    url: list_url,
    data: formData,
    withCredentials: false,
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Token nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn"
    }
  })

  return (
    <Row>
      <Col>
        <h1>Add a new {model_name} "{list_url}"</h1>
        <Card>
          <Card.Body>
            <Card.Title>{model_name_title}</Card.Title>
              <Form
                action={list_url}
                method="post"
                schema={post_schema}
                validator={validator}
                formData={formData}
                onChange={e => setFormData(Object.assign(e.formData, {"csrfmiddlewaretoken": csrf_token}))}
                onSubmit={onSubmit}
              >
                <Button type="submit">Create</Button>
            </Form>
          </Card.Body>
        </Card>
      </Col>
    </Row>
  );
}
