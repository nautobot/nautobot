import axios from "axios"
import { Button, Frame, Text } from "@nautobot/nautobot-ui"
import { Card, CardHeader, CardBody } from "@chakra-ui/react"
import Cookies from 'js-cookie'
import { useState } from "react"
// import { RJSFSchema } from "@rjsf/utils";
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
  // const ui_schema = data.serializer.uiSchema
  // const log = (type) => console.log.bind(console, type)
  const model_name_title = post_schema.title
  const model_name = model_name_title.toLowerCase()

  // Using axios so that we can do a POST.
  const onSubmit = ({formData}) => axios({
    method: "post",
    url: list_url,
    data: formData,
    withCredentials: false,
    // TODO: obviously this can't ship with a hard-coded API token... see issue #3242
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Token " + process.env.NAUTOBOT_API_TOKEN
    }
  })

  return (
    <Frame>
      <Card>
        <CardHeader>Add a new {model_name} "{list_url}"</CardHeader>
        <CardBody>
          <Text>{model_name_title}</Text>
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
        </CardBody>
      </Card>
    </Frame>
  );
}
