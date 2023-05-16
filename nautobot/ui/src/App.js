import { useEffect } from "react";
import { BrowserRouter } from "react-router-dom";
import { NautobotUIProvider } from "@nautobot/nautobot-ui";
import { useDispatch } from "react-redux";
import { useGetSessionQuery, useGetUIMenuQuery } from "@utils/api";
import { updateAuthStateWithSession, updateNavigation } from "@utils/store";

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
    const { data: sessionData, isSuccess: isSessionSuccess } =
        useGetSessionQuery();
    const { data: menuData, isSuccess: isMenuSuccess } = useGetUIMenuQuery();

    useEffect(() => {
        // TODO: Do we need special handling for non-successful session requests?
        if (isSessionSuccess) {
            dispatch(updateAuthStateWithSession(sessionData));
        }
        return;
    }, [dispatch, sessionData, isSessionSuccess]);

    useEffect(() => {
        // TODO: Do we need special handling for non-successful menu requests?
        if (isMenuSuccess) {
            dispatch(updateNavigation(menuData));
        }
        return;
    }, [dispatch, menuData, isMenuSuccess]);

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
