import './App.css';
import Menu from "./common/components/menu";
import { Container } from "react-bootstrap";
import Alert from "react-bootstrap/Alert";
import { Route, Routes, NavLink, HashRouter, BrowserRouter } from "react-router-dom";
import ListViewTemplate from 'common/template/ListViewTemplate';
import { Component } from "react";

class App extends Component {
  render() {
    return (
      <div className="">
        <BrowserRouter>
          <Menu />
          <Container fluid="sm" className='page-container'>

            <Alert variant="success" style={{ textAlign: "center" }}>
              Example Plugin says “Hello, admin!” 👋 <br />
            </Alert>
            <Routes>
              <Route path="/" />
              <Route path="/dcim/sites" element={<ListViewTemplate />} />
            </Routes>
          </Container>

          <footer>
          </footer>

        </BrowserRouter>
      </div>
    );
  }
}

export default App;
