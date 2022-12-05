import {
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    TableContainer,
    Stack,
} from '@chakra-ui/react'
import { Link } from 'react-router-dom'
import LinkedIcon from "@core/LinkedIcon";

export default function NautobotTable({ header_coloums, body_coloums, buttons }) {
    return (
        <TableContainer>
            <Table variant='striped'>
                <Thead bg="blackAlpha.900">
                    <Tr>
                        {
                            header_coloums.map((item, idx) => (
                                <Th key={idx} color="white">{item.label}</Th>
                            ))
                        }
                        {
                            buttons ?
                                (
                                    <Th color="white">Action</Th>
                                )
                                :
                                null
                        }
                    </Tr>
                </Thead>
                <Tbody>
                    {
                        body_coloums.map((item, idx) => (
                            <Tr key={idx}>
                                {
                                    header_coloums.map((header, idx) => (
                                        <Td key={idx}>
                                            {
                                                item[header.name] == null ?
                                                "-"
                                                :
                                                Array.isArray(item[header.name]) ?
                                                item[header.name].join(", ")
                                                :
                                                typeof(item[header.name]) == "object" ?
                                                item[header.name].label || item[header.name].display
                                                :
                                                idx === 0 ?
                                                <Link to={"/"}>{item[header.name]}</Link>
                                                :
                                                item[header.name]
                                            }
                                        </Td>
                                    ))
                                }
                                {
                                    buttons ?
                                        (
                                            <Td>
                                                <Stack direction='row' spacing={2} align='center'>
                                                {
                                                    buttons.map((btn_data, idx) => (
                                                        <LinkedIcon
                                                            key={idx}
                                                            icon={btn_data["icon"]}
                                                            link={item["base_url"]}
                                                            tooltip={btn_data["tooltip"]}
                                                        />
                                                    ))
                                                }
                                                </Stack>
                                            </Td>
                                        )
                                        :
                                        null
                                }

                            </Tr>
                        ))
                    }
                </Tbody>
            </Table>
        </TableContainer>
    )
}