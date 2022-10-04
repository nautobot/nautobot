import { useState, useEffect } from "react";
import { useRouter } from "next/router";
//react-bootstrap
import Row from "react-bootstrap/Row";
import Col from "react-bootstrap/Col";
import Card from "react-bootstrap/Card";
import Stack from "react-bootstrap/Stack";
import Button from "react-bootstrap/Button";
import Container from "react-bootstrap/Container";
//pages
import Home from "../../pages";
//shared
import NautobotInput from "@shared/NautobotInput";
import NautobotSelect from "@shared/NautobotSelect";
//utils
import { axios_instance } from "@utils/utils";
import { inputTypes } from "@utils/constants";
import { capitalize } from "@utils/helpers";

export default function CreateViewTemplate({ pageTitle, children }, props) {
  const router = useRouter();

  const [pageConfig, setPageConfig] = useState({
    form_fields: require("../../common/utils/api/sites/add-form-fields.json"),
  });
  const [formFields, setFormFields] = useState({});

  useEffect(async () => {
    const form_fields_url =
      location.pathname.replace("add", "") + "form-fields/";
    const formFields = await axios_instance.get(form_fields_url);
    setFormFields(formFields.data);
  }, []);

  const cancelHandler = () => {
    const pathname = router.pathname.split("/");
    const newPath = pathname.slice(0, pathname.length - 1).join("/");
    router.push(`${newPath}`);
  };

  const createHandler = () => {};

  const createAndAddNewHandler = () => {
    router.push(`${router.pathname}`);
  };

  return (
    <Home pageTitle={pageTitle}>
      <Container>
        <Row className="justify-content-md-center">
          <Col xs lg="7">
            {!children ? (
              <>
                <h4>Add New</h4>
                {Object.entries(formFields).map((group, idx) => (
                  <Card className="mb-4" key={idx}>
                    <Card.Header>
                      <b>{group[0]}</b>
                    </Card.Header>
                    {/* <Card.Body>
                      {group[1].map((field, idx) =>
                        field ? (
                          ["char-field", "integer-field", "others"].includes(
                            field.type
                          ) ? (
                            <NautobotInput
                              key={idx}
                              _type="text"
                              label={field.label}
                            />
                          ) : field.type == "dynamic-choice-field" ? (
                            <NautobotSelect
                              key={idx}
                              label={field.label}
                              options={field.choices}
                            />
                          ) : (
                            <NautobotInput
                              key={idx}
                              _type="checkbox"
                              label=""
                            />
                          )
                        ) : (
                          <></>
                        )
                      )}
                    </Card.Body> */}
                    <Card.Body>
                      {group[1].map((field, idx) =>
                        field ? (
                          field.type === "dynamic-choice-field" ? (
                            <NautobotSelect
                              key={idx}
                              label={capitalize(field.label)}
                              options={field.choices}
                              helpText={field.help_text}
                              fieldName={field.field_name}
                              required={field.required}
                            />
                          ) : (
                            <NautobotInput
                              key={idx}
                              _type={inputTypes[field.type]}
                              label={capitalize(field.label)}
                              helpText={field.help_text}
                              fieldName={field.field_name}
                              required={field.required}
                              hideInput={false}
                            />
                          )
                        ) : (
                          null
                        )
                      )}
                    </Card.Body>
                  </Card>
                ))}
              </>
            ) : (
              children
            )}
            <Stack
              direction="horizontal"
              gap={1}
              className="justify-content-end"
            >
              <Button variant="primary" onClick={createHandler}>
                Create
              </Button>
              <Button variant="primary" onClick={createAndAddNewHandler}>
                Create and Add New
              </Button>
              <Button variant="outline-dark" onClick={cancelHandler}>
                Cancel
              </Button>
            </Stack>
          </Col>
        </Row>
      </Container>
    </Home>
  );
}
