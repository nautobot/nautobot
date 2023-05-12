import React from "react";
import { BrowserRouter } from "react-router-dom";
import { NautobotUIProvider } from "@nautobot/nautobot-ui";
import { useDispatch } from "react-redux";
import { useGetSessionQuery } from "@utils/api";
import { updateSessionState } from "@utils/store";

import Layout from "@components/Layout";
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
    const dispatch = useDispatch();
    const {
        data: sessionData,
        isSuccess: isSessionSuccess,
        isError: isSessionError,
    } = useGetSessionQuery();

    React.useEffect(() => {
        if (!isSessionSuccess || isSessionError) {
            return;
        }
        if (isSessionSuccess) {
            dispatch(updateSessionState(sessionData));
        }
    }, [dispatch, sessionData, isSessionSuccess, isSessionError]);

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
