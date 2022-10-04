import { useState, useEffect } from "react";
//react-bootstrap
import Row from "react-bootstrap/Row";
import Col from "react-bootstrap/Col";
import Form from "react-bootstrap/Form";

export default function NautobotInput({
  _type,
  label,
  placeholder,
  helpText,
  fieldName,
  required,
  hideInput,
  id,
  func,
}) {
  const [value, setValue] = useState("");

  const handleChange = (e) => {
    setValue(e.target.value);
  };

  useEffect(() => {
    func && func(value);
  }, [value]);

  return hideInput ? null : (
    <div id={id}>
      <Form.Group as={Row} className="mb-2" controlId={`control-${id}`}>
        <Form.Label column sm="3">
          {label}
        </Form.Label>
        <Col sm="9">
          {_type === "textarea" ? (
            <Form.Control
              as="textarea"
              rows={3}
              placeholder={placeholder || label}
              required={required}
              value={value}
              onChange={handleChange}
            />
          ) : (
            <Form.Control
              type={_type}
              placeholder={placeholder || label}
              required={required}
              value={value}
              onChange={handleChange}
            />
          )}
          <Form.Text muted>{helpText}</Form.Text>
        </Col>
      </Form.Group>
    </div>
  );
}
