import "./App.css";
import { Component } from "react";
import Container from "react-bootstrap/Container";
import Alert from "react-bootstrap/Alert";
import Menu from "./common/components/menu";

class App extends Component {
  render() {
    return (
      <div className="">
        <Menu />
        <Container fluid="sm" className='page-container'>

          <Alert variant="success" style={{ textAlign: "center" }}>
            Example Plugin says “Hello, admin!” 👋 <br />
          </Alert>
          {this.props.children}
        </Container>

        <footer>
        </footer>

      </div>
    );
  }
}

export default App;
