import React from "react";
import Tab from "react-bootstrap/Tab"
import { nautobot_url } from "../../index"
import useSWR from "swr"

class RenderTabContent extends React.Component {
    constructor(props) {
        super(props);
        this.tab = props.tab

        this.state = {
            html: ""
        }
    }
    // meatandpotatoes

    componentDidMount() {
        const fetchTabHTML = async () => {
            const resp = await fetch(nautobot_url + this.tab.url, { credentials: "include" });
            const payload = await resp.text();

            var parser = new DOMParser();
            var doc = parser.parseFromString(payload, 'text/html');

            this.setState({
                html: doc.getElementById('meatandpotatoes').outerHTML
            })
        }
        fetchTabHTML()
    }
    render() {
        
        return (<div dangerouslySetInnerHTML={{__html: this.state.html}} />);
    }
}

export default function create_plugin_tab(props) {
    let tab=props.tab
    return (
        <Tab title={tab.title} eventKey={tab.title}><RenderTabContent tab={tab}/></Tab>
    )
}