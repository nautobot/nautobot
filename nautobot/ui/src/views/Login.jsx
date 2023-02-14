import { Button, Card, Col, Form, Row } from "react-bootstrap"
import Cookies from "js-cookie"


export default function Login() {
  const csrf_token = Cookies.get("csrftoken")
  return (
    <Row style={{ marginTop: "150px" }}>
      <Col sm={{ span: 4, offset: 4 }}>
        <Form action="/login/" method="POST">
          <Card>
            <Card.Header>Log In</Card.Header>
            <Card.Body>
              <Form.Control type="hidden" name="csrfmiddlewaretoken" value={csrf_token} />
              <Form.Group controlId="id_username">
                <Form.Label>Username</Form.Label>
                <Form.Control type="text" name="username" autoCapitalize="none" autoFocus autoComplete="username" maxLength={150} required />
              </Form.Group>
              <Form.Group controlId="id_password">
                <Form.Label>Password</Form.Label>
                <Form.Control type="password" name="password" autoCapitalize="none" autoComplete="current-password" required />
              </Form.Group>
            </Card.Body>
            <Card.Footer className="text-end">
              <Button type="submit">Log In</Button>
            </Card.Footer>
          </Card>
        </Form>
      </Col>
    </Row>
  )
}
