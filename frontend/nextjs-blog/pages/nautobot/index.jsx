import Home from ".."
import Alert from 'react-bootstrap/Alert';


export default function NautobotHome() {
    return (
        <Home>
            <Alert variant="primary" style={{textAlign: "center"}}>
                Example Plugin says “Hello, admin!” 👋
            </Alert>
            <div>
                <h1>
                    HELLO THIS IS THE CORE VIEW
                </h1>
            </div>
          
      </Home>
    )
}