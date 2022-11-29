//react-bootstrap
import Table from "react-bootstrap/Table";
import { Link } from "react-router-dom";

export default function NautobotTable({ data, header }) {
  return (
    <Table striped>
      <thead>
        <tr>
          <th>
            <input type="checkbox" name="" id="" />
          </th>
          {header.map(({ name, label }) => (
            <th key={name}>{label}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((item) => (
          <tr key={item.id}>
            <td>
              <input type="checkbox" name="" id="" />
            </td>
            {header.map((header, idx) => (
              <td key={idx}>
                {item[header.name] == null
                  ? "-"
                  : Array.isArray(item[header.name])
                    ? item[header.name].join(", ")
                    : typeof item[header.name] == "object"
                      ? item[header.name].label || item[header.name].display
                      : idx === 0
                        ? <Link to={item["id"]}>{item[header.name]}</Link>
                        : item[header.name]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
