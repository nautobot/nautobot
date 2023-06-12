import {Box, Heading, NtcThumbnailIcon, Table, TableContainer, Tbody, Thead, Tr, Th, Td } from '@nautobot/nautobot-ui';
import GenericView from "@views/generic/GenericView";
import { useParams } from "react-router-dom";
import { toTitleCase } from "@utils/string";
import { ObjectTableItem } from "@components";

export default function ModelView(props) {
  const { app_name, model_name } = useParams();
  return (
  <GenericView>
    <Box background="white-0" borderRadius="md" padding="md">
    <Heading
        as="h1"
        size="H1"
        display="flex"
        alignItems="center"
        gap="5px"
        pb="sm"
    >
        <NtcThumbnailIcon width="25px" height="30px" />{" "}
        Overridden Retrieve View for {toTitleCase(model_name, "-")}
    </Heading>
      <TableContainer>
        <Table>
              <Thead>
                <Th>Key</Th>
                <Th>Value</Th>
              </Thead>
            <Tbody>
              {Object.entries(props).map(([k, v]) => (
                  [<Tr>
                      <Td>
                          <strong>{k}</strong>
                      </Td>
                      <Td>
                          <ObjectTableItem obj={v} />
                      </Td>
                  </Tr>]
              ))
              }
            </Tbody>
          </Table>
      </TableContainer>

    </Box>

    </GenericView>
  );
}