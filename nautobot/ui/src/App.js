import React from "react";
import { BrowserRouter } from "react-router-dom";
import { NautobotUIProvider } from "@nautobot/nautobot-ui";

import Layout from "@components/layouts/Layout";
import NautobotRouter from "./router";

const theme = {
    fonts: {
        heading: `'Ubuntu', sans-serif`,
        body: `'Ubuntu', sans-serif`,
        mono: `'Ubuntu Mono', monospace`,
    },

    styles: {
        global: {
            "html, body, #root": {
                height: "full",
                width: "full",
            },
        },
    },
};

// TODO: See if we can/need to continue this pattern:
// Global API pattern needs these arguments passed through:
//   { updateStore, globalApi }
// (see index.js for context)

function App() {
    return (
        <NautobotUIProvider theme={theme}>
            <BrowserRouter>
                <Layout>
                    <NautobotRouter />
                </Layout>
            </BrowserRouter>
        </NautobotUIProvider>
    );
}

export default App;
