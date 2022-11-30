import { MDBContainer } from 'mdb-react-ui-kit';

import NavBar from "@common/NavBar";


export default function BaseLayout(props){
    return (
        <div>
            <NavBar />
            <MDBContainer fluid className='body'>
                {props.children}
            </MDBContainer>
        </div>
    )
}