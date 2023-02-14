import { Form, Table } from "react-bootstrap"

import BSTableItem from "@components/core/BSTableItem"


export default function NautobotTable({ data, headers }) {
  return (
    <Table hover responsive>
      <thead>
        <tr>
          <th>
            <Form.Check type="checkbox" className="" id="" />
          </th>
          {headers.map(({ name, label }) => (
            <th key={name}>{label}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((item) => (
          <tr key={item.id}>
            <td>
              <Form.Check type="checkbox" className="" id="" />
            </td>
            {headers.map((header, idx) => (
              <td key={idx}>
                <BSTableItem
                  name={header.name}
                  obj={item[header.name]}
                  url={window.location.pathname + item["id"]}
                  link={idx === 0}
                />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
