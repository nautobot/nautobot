import Table from 'react-bootstrap/Table';


export default function NautobotTable(props) {
    return (
        <Table striped>
            <thead>
                <tr>
                    <th><input type="checkbox" name="" id="" /></th>
                    {
                        props.header.map((item, idx) => (
                            <th key={idx}>{item.label}</th>
                        ))
                    }
                </tr>
            </thead>
            <tbody>
                {
                    props.data.map((item) => (
                        <tr key={item.id}>
                            <td><input type="checkbox" name="" id="" /></td>
                            {
                                props.header.map((header, idx) => (
                                    <td key={idx}>
                                        {
                                            item[header.name] == null ?
                                                "-"
                                                :
                                                Array.isArray(item[header.name]) ?
                                                    item[header.name].join(", ")
                                                    :
                                                    typeof (item[header.name]) == "object" ?
                                                        item[header.name].label || item[header.name].display
                                                        :
                                                        item[header.name]
                                        }
                                    </td>
                                ))
                            }
                        </tr>
                    ))
                }
            </tbody>
        </Table>
    )
}
