import { Button, Card, Col, Form, Row } from "react-bootstrap"
import axios from "axios"


export default function Login() {
  const handleSubmit = (e) => {
    e.preventDefault();
    axios.post(
      '/api/users/tokens/authenticate/', {
        username: e.target.username.value,
        password: e.target.password.value,
      })
      .then(res => localStorage.setItem("nautobot-user", e.target.username.value))
      .catch(err => alert(err.detail))
  }
  return (
    <Row style={{ marginTop: "150px" }}>
      <Col sm={{ span: 4, offset: 4 }}>
        <Form method="POST" onSubmit={handleSubmit}>
          <Card>
            <Card.Header>Log In</Card.Header>
            <Card.Body>
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
