import {
    MDBContainer,
    MDBInputGroup,
    MDBBtn,
} from 'mdb-react-ui-kit';
import {
    Breadcrumb,
    BreadcrumbItem,
    BreadcrumbLink,
    Grid, 
    GridItem,
    Heading,
    Button, 
    ButtonGroup,
} from '@chakra-ui/react'



export default function ListViewLayout(props) {
    return (
        <MDBContainer fluid className='body'>
            {/* Breadcrub */}
            <Grid templateColumns='repeat(8, 1fr)' gap={2}>
                <GridItem colSpan={6} className='breadcrumb-grid' h='10'>
                    <Breadcrumb>
                        <BreadcrumbItem fontSize="medium">
                            <BreadcrumbLink href='#'>{props.page_title}</BreadcrumbLink>
                        </BreadcrumbItem>
                    </Breadcrumb>
                </GridItem>
                <GridItem colSpan={2}>
                    <MDBInputGroup className='mb-3'>
                        <input className='form-control' placeholder={"Search " + props.page_title} type='text' />
                        <MDBBtn className='nautobot-primary'>Search</MDBBtn>
                    </MDBInputGroup>
                </GridItem>
            </Grid>

            {/* Page title and buttons */}
            <Grid templateColumns='repeat(8, 1fr)' gap={2} marginTop={3}>
                <GridItem colSpan={2}>
                    <Heading as='h3' size='lg'>{props.page_title}</Heading>
                </GridItem>
                <GridItem>
                    {/* <Button colorScheme='gray' variant='outline'>Email</Button> */}
                </GridItem>
            </Grid>
        
            {props.children}
        </MDBContainer>
    )
}