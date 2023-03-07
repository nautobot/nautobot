import { Checkbox, Table, Thead, Tr, Th, Tbody, Td } from "@nautobot/nautobot-ui"

import BSTableItem from "@components/core/BSTableItem"


export default function NautobotTable({ data, headers }) {
  return (
    <Table>
      <Thead>
        <Tr>
          <Th>
            <Checkbox></Checkbox>
          </Th>
          {headers.map(({ name, label }) => (
            <Th key={name}>{label}</Th>
          ))}
        </Tr>
      </Thead>
      <Tbody>
        {data.map((item) => (
          <Tr key={item.id}>
            <Td>
              <Checkbox></Checkbox>
            </Td>
            {headers.map((header, idx) => (
              <Td key={idx}>
                <BSTableItem
                  name={header.name}
                  obj={item[header.name]}
                  url={window.location.pathname + item["id"]}
                  link={idx === 0}
                />
              </Td>
            ))}
          </Tr>
        ))}
      </Tbody>
    </Table>
  );
}
