import React from 'react';
import ReactDOM from 'react-dom/client';
import reportWebVitals from './reportWebVitals';
import { BrowserRouter } from "react-router-dom";
import NautobotRouter from './router';

import "./styles/globals.css"
import "bootstrap/dist/css/bootstrap.css"
import Layout from '@components/layouts/BSLayout';
const dev = process.env.NODE_ENV !== "production"
export const nautobot_url = dev ? "http://localhost:8080" : ""

/**
 * Adds capitalize method to string
 *
 * TODO: Useful utility but extending String.prototype isn't recommended
 */
// Object.defineProperty(String.prototype, 'capitalize', {
//   value: function () {
//       let values = this.split("-").map(text => text.charAt(0).toUpperCase() + text.slice(1))
//       return values.join(" ");
//   },
//   enumerable: false
// });

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <Layout>
        <NautobotRouter />
      </Layout>
    </BrowserRouter>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
