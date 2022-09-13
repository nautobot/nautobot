import Table from 'react-bootstrap/Table';
import Link from 'next/link';


export default function NautobotTable(props){
    return (
        <Table striped>
            <thead>
                <tr>
                    <th><input type="checkbox" name="" id="" /></th>
                    {
                        props.header.map((item, idx) => (
                            <th key={idx}>{item}</th>
                        ))
                    }
                </tr>
            </thead>
            <tbody>
                {
                    props.data.map((item, idx) => (
                        <tr key={idx}>
                            <td><input type="checkbox" name="" id="" /></td>
                            {
                                Object.entries(item).map((value, idx) => (
                                    <td key={idx}>
                                        {
                                            idx == 0 ? 
                                            <Link href="#" style={{textDecoration: "none"}}> 
                                                {value[1]}
                                            </Link>
                                            : 
                                            value[1]
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