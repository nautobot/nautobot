import { Card, CardHeader, CardBody } from "@chakra-ui/react"; // TODO import from nautobot-ui when available
import { Button, Frame } from "@nautobot/nautobot-ui";
import Form from "@rjsf/chakra-ui";
import validator from "@rjsf/validator-ajv8";
import axios from "axios";
import { useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import useSWR from "swr";

import { uiUrl } from "@utils/url";
import GenericView from "@views/generic/GenericView";

const fetcher = (url) =>
    axios.options(url, { withCredentials: true }).then((res) => res.data);

export default function GenericObjectCreateView({ list_url }) {
    const { app_label, model_name } = useParams();
    const location = useLocation();
    const [formData, setFormData] = useState(null);
    const [extraErrors, setExtraErrors] = useState({});
    const isPluginView = location.pathname.includes("/plugins/");
    const pluginPrefix = isPluginView ? "plugins/" : "";

    if (!list_url) {
        list_url = `/api/${pluginPrefix}${app_label}/${model_name}/`;
    }

    const { data, error } = useSWR(list_url, fetcher);

    if (!app_label || !model_name) {
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
                window.location.href = uiUrl(res.data.url);
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

    return (
        <GenericView>
            <Frame>
                <Card>
                    <CardHeader>Add a new {data.schema.title}</CardHeader>
                    <CardBody>
                        <Form
                            action={list_url}
                            schema={data.schema}
                            uiSchema={data.uiSchema}
                            validator={validator}
                            formData={formData}
                            onChange={(e) => {
                                setFormData(Object.assign(e.formData));
                                setExtraErrors({});
                            }}
                            onSubmit={onSubmit}
                            extraErrors={extraErrors}
                        >
                            <Button type="submit">Create</Button>
                        </Form>
                    </CardBody>
                </Card>
            </Frame>
        </GenericView>
    );
}
