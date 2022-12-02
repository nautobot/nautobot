import React from 'react';
import ReactDOM from 'react-dom/client';
import reportWebVitals from './reportWebVitals';
import { BrowserRouter } from "react-router-dom";
import { ChakraProvider } from '@chakra-ui/react'
import { MDBContainer } from 'mdb-react-ui-kit';

import 'mdb-react-ui-kit/dist/css/mdb.min.css';
import "@fortawesome/fontawesome-free/css/all.min.css";
import "./index.css"

import NautobotRouter from './router';
import NavBar from '@components/common/NavBar';

/**
 * Adds capitalize method to string
 */
Object.defineProperty(String.prototype, 'capitalize', {
  value: function () {
      let values = this.split("-").map(text => text.charAt(0).toUpperCase() + text.slice(1))
      return values.join(" ");
  },
  enumerable: false
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <ChakraProvider>
      <BrowserRouter>
        <NavBar />
        <MDBContainer fluid className='body'>
          <NautobotRouter />
        </MDBContainer>
      </BrowserRouter>
    </ChakraProvider>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
