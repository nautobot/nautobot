import CreateViewTemplate from "../../../common/template/create-view"
import Card from 'react-bootstrap/Card';
import NautobotInput from "../../../common/components/nautobot-default-input"

export default function ExamplePluginAdd(){
    return (
        <CreateViewTemplate>
            <h4>Add a new example plugin model</h4>
            <Card className="mb-4">
                <Card.Header><b>Example Custom Form</b></Card.Header>
                <Card.Body>
                    <NautobotInput _type="text" label="Item 1" />
                    <NautobotInput _type="text" label="Item 2" />
                    <NautobotInput _type="select" label="Item 3" options={[{"label": "Sammy", "value": "sammy"}]} />
                </Card.Body>
            </Card>

        </CreateViewTemplate>
    )
}