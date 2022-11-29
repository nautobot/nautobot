import Form from "react-bootstrap/Form";

export default function NautobotCheck({ label, _type }) {
  return (
    <Form.Group>
      <Form.Check type={_type} label={label} />
    </Form.Group>
  );
}
