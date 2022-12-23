import Tab from "react-bootstrap/Tab"

export default function PluginTab(props) {
    console.log("tacos")
    console.log(props.tab)
    let tab=props.tab
    return (
        <Tab title={tab.title} eventKey={tab.title}><div dangerouslySetInnerHTML={{__html: "<p>I can be retrieved from "+tab.url+"</p>"}} /></Tab>
    )
}