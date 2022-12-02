import {
    Table,
    Thead,
    Tbody,
    Tfoot,
    Tr,
    Th,
    Td,
    TableCaption,
    TableContainer,
    Checkbox,
} from '@chakra-ui/react'
import { Link } from 'react-router-dom'
import { useEffect } from 'react'

export default function NautobotTable({ header_coloums, body_coloums }) {
    return (
        <TableContainer>
            <Table variant='striped'>
                <Thead bg="blackAlpha.900">
                    <Tr>
                        <Th color="white"><Checkbox /></Th>
                        {
                            header_coloums.map((item, idx) => (
                                <Th key={idx} color="white">{item.label}</Th>
                            ))
                        }
                    </Tr>
                </Thead>
                <Tbody>
                    {
                        body_coloums.map((item, idx) => (
                            <Tr key={idx}>
                                <Td><Checkbox /></Td>
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
                            </Tr>

                        ))
                    }
                </Tbody>
                <Tfoot>
                    <Tr>
                        <Th>To convert</Th>
                    </Tr>
                </Tfoot>
            </Table>
        </TableContainer>

    )
}