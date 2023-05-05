import { Card, CardHeader, CardBody } from "@chakra-ui/react"; // TODO import from nautobot-ui when available
import { Box, Button, Frame, Heading, NtcThumbnailIcon } from "@nautobot/nautobot-ui";
import Form from "@rjsf/chakra-ui";
import validator from "@rjsf/validator-ajv8";
import axios from "axios";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import useSWR from "swr";
import { useEffect, useState } from "react";

import GenericView from "@views/generic/GenericView";
import { uiSchema, widget } from "./ui_schema_sample.js";


const TitleFieldTemplate = (props) => {
    const { id, required, title } = props;
    return (
        <Heading 
            as="h4"
            size="H4"
            display="flex"
            alignItems="center"
            gap="5px"
            id={id}
            fontWeight={500}
        >
            <NtcThumbnailIcon width="25px" height="30px" /> {title}
        </Heading>
    );
}



const fetcher = (url) =>
    axios.options(url, { withCredentials: true }).then((res) => res.data);

export default function GenericObjectCreateView({ list_url }) {
    const { app_name, model_name } = useParams();
    const location = useLocation();
    const [formData, setFormData] = useState(null);
    const [extraErrors, setExtraErrors] = useState({});
    const navigate = useNavigate();
    const isPluginView = location.pathname.includes("/plugins/");
    const pluginPrefix = isPluginView ? "plugins/" : "";

    if (!list_url) {
        list_url = `/api/${pluginPrefix}${app_name}/${model_name}/`;
    }

    const { data, error } = useSWR(list_url, fetcher);

    if (!app_name || !model_name) {
        return <GenericView />;
    }

    if (error) {
        return (
            <GenericView>
                <div>Failed to load schema from {list_url}</div>
            </GenericView>
        );
    }

    if (!data) return <GenericView />;

    const post_schema = data.schema;
    // uiSchema is used how the form will be presented.
    const ui_schema = data.uiSchema;
    const model_name_title = post_schema.title;

    // Using axios so that we can do a POST.
    const onSubmit = ({ formData }) => {
        setExtraErrors({});
        axios({
            method: "post",
            url: list_url,
            data: formData,
            withCredentials: true,
            headers: {
                "Content-Type": "application/json",
            },
        })
            .then(function (res) {
                navigate(res.data.web_url);
            })
            .catch((error) => {
                let errors = Object.fromEntries(
                    Object.entries(error.response.data).map(([k, v], i) => [
                        k,
                        { __errors: v },
                    ])
                );
                setExtraErrors(errors);
            });
    };
// utilis/color.js
    return (
        <GenericView>
            <Box
                background="white-0"
                borderRadius="md"
                padding="md"
            >
                <Card>
                    <Heading
                        as="h1"
                        size="H1"
                        display="flex"
                        alignItems="center"
                        gap="5px"
                        pb="sm"
                    >
                        <NtcThumbnailIcon width="25px" height="30px" /> Add a new {model_name_title}
                    </Heading>
                    <CardBody>
                        <Form
                            action={list_url}
                            schema={post_schema}
                            uiSchema={ui_schema}
                            validator={validator}
                            formData={formData}
                            widgets={widget}
                            onChange={(e) => {
                                setFormData(Object.assign(e.formData));
                                setExtraErrors({});
                            }}
                            onSubmit={onSubmit}
                            extraErrors={extraErrors}
                            className="nautobot-add-form"
                            templates={{TitleFieldTemplate}}
                        >
                            <Button type="submit" mt="2rem"><NtcThumbnailIcon width="25px" height="30px" />Create</Button>
                        </Form>
                    </CardBody>
                </Card>
            </Box>
        </GenericView>
    );
}
