import React from "react";
import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";
import { store } from "@utils/store";
import { PersistGate } from "redux-persist/integration/react";
import { persistStore } from "redux-persist";

import reportWebVitals from "./reportWebVitals";
import App from "./App";

import "@fontsource/ubuntu/400.css";
import "@fontsource/ubuntu/500.css";
import "@fontsource/ubuntu-mono/400.css";

// const dev = process.env.NODE_ENV !== "production";
const container = document.getElementById("root");
const root = createRoot(container);

let persistor = persistStore(store);

// ===
// Establish a Global API because the one we create at startup/build time
//   won't have all of the endpoints. Can't have async/await at the top
//   so we can't wait to define the entire API until after the first API call
//
// TODO: Either investigate dynamic loading API or getting the scheme at startup
//    Can't tell if the failure to subscribe to events in components is due to dynamic API
//    or if this pattern won't work
//
// -- Imports for this pattern
// import { rootReducer } from '@utils/store';
// import { addMiddleware, removeMiddleware } from 'redux-dynamic-middlewares'
// import { baseApi } from "@utils/apiSlice";
// import { combineReducers } from 'redux'
// import sessionReducer from '@utils/session'
// ---
//
// let globalStore = store
// export let globalApi = baseApi

// function updateStore(newApi) {
//   globalApi = newApi
//   globalStore.replaceReducer(combineReducers({
//     session: sessionReducer,
//     [globalApi.reducerPath]: globalApi.reducer,
//   }))
//   removeMiddleware(baseApi.middleware)
//   addMiddleware(globalApi.middleware)
// }
/// ===

root.render(
    <React.StrictMode>
        <Provider store={store}>
            <PersistGate loading={null} persistor={persistor}>
                <App />
            </PersistGate>
        </Provider>
    </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
