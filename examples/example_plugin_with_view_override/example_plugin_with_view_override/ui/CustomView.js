import { Table, Box, TableContainer, Tbody, Thead, Tr, Th, Td } from '@nautobot/nautobot-ui';
import GenericView from "@views/generic/GenericView";

export default function CustomTableView(props) {
  return (
  <GenericView>
    <Box background="white-0" borderRadius="md" padding="md">
      <TableContainer>
        <Table>
              <Thead>
                <Th>Key</Th>
                <Th>Value</Th>
              </Thead>
            <Tbody>
              <Tr>
                <Td>ID</Td>
                <Td>{props.id}</Td>
              </Tr>
              <Tr>
                <Td>Display</Td>
                <Td>{props.display}</Td>
              </Tr>
              <Tr>
                <Td>URL</Td>
                <Td>{props.url}</Td>
              </Tr>
            </Tbody>
          </Table>
      </TableContainer>

    </Box>

    </GenericView>
  );
}
