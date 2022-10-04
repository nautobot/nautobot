import { useState, useEffect } from "react";
//react-bootstrap
import Row from "react-bootstrap/Row";
import Col from "react-bootstrap/Col";
import Form from "react-bootstrap/Form";

export default function NautobotSelect({
  label,
  options,
  placeholder,
  helpText,
  fieldName,
  required,
  hideInputId,
  hideIsValue,
}) {
  const [value, setValue] = useState(options[0]);

  useEffect(() => {
    const hideInputElement = document.getElementById(hideInputId);
    if (value === hideIsValue && hideInputElement) {
      hideInputElement.style.display = "none";
    } else if (hideInputElement) {
      hideInputElement.style.display = "block";
    }
  }, [value]);

  return (
    <Form.Group as={Row} className="mb-3" controlId="formBasicSelect">
      <Form.Label column sm={3}>
        {label}
      </Form.Label>
      <Col sm={9}>
        <Form.Select
          value={value}
          onChange={(e) => setValue(e.target.value)}
          aria-label="Default select example"
          required={required}
        >
          {/* <option>------</option> */}
          {options.map(({ label, value }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Form.Select>
      </Col>
      <Form.Text muted>{helpText}</Form.Text>
    </Form.Group>
  );
}
