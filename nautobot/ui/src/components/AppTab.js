import React from "react";
import { Tab } from "@nautobot/nautobot-ui";

class RenderTabContent extends React.Component {
    constructor(props) {
        super(props);
        this.tab = props.tab;

        this.state = {
            html: "",
        };
    }

    componentDidMount() {
        const fetchTabHTML = async () => {
            const resp = await fetch(this.tab.url, { credentials: "include" });
            const payload = await resp.text();

            var parser = new DOMParser();
            var doc = parser.parseFromString(payload, "text/html");

            this.setState({
                html: doc.getElementById("legacy-content").innerHTML,
            });
        };
        fetchTabHTML();
    }
    render() {
        return <div dangerouslySetInnerHTML={{ __html: this.state.html }} />;
    }
}

export default function create_app_tab(props) {
    let tab = props.tab;
    return (
        <Tab title={tab.title} eventKey={tab.title} key={tab.title}>
            <RenderTabContent tab={tab} />
        </Tab>
    );
}
