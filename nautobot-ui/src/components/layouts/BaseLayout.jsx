import { MDBContainer } from 'mdb-react-ui-kit';


export default function BaseLayout(props){
    return (
        <div>
            <MDBContainer fluid className='body'>
                {props.children}
            </MDBContainer>
        </div>
    )
}