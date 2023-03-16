import React from "react"
import { createRoot } from "react-dom/client"
import { Provider } from 'react-redux';
import { store } from '@utils/store';
import App from './App';
import reportWebVitals from "src/reportWebVitals"
import "src/styles/globals.css"


const dev = process.env.NODE_ENV !== "production"

const container = document.getElementById('root')
const root = createRoot(container);

root.render(
  <React.StrictMode>
    <Provider store={store}>
      <App />
    </Provider>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
