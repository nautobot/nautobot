import { useEffect } from "react";
import { BrowserRouter } from "react-router-dom";
import { useDispatch } from "react-redux";
import { NautobotUIProvider } from "@nautobot/nautobot-ui";

import Layout from "@components/Layout";
import { useGetSessionQuery, useGetUIMenuQuery } from "@utils/api";
import { updateAuthStateWithSession, updateNavigation } from "@utils/store";

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

function App() {
    const dispatch = useDispatch();

    // Because the entire application is dependent on the session and menu data,
    // bind the entire application to the success of these queries.
    //
    // When we have successfully retrieved the session data, update the auth state
    // and refetch the menu data.
    const { data: sessionData, isSuccess: isSessionSuccess } =
        useGetSessionQuery();
    const {
        data: menuData,
        isSuccess: isMenuSuccess,
        refetch: refetchMenuQuery,
    } = useGetUIMenuQuery();

    useEffect(() => {
        if (isSessionSuccess) {
            dispatch(updateAuthStateWithSession(sessionData));
            dispatch(refetchMenuQuery);
        }
        return;
    }, [dispatch, sessionData, isSessionSuccess, refetchMenuQuery]);

    useEffect(() => {
        if (isMenuSuccess) {
            dispatch(updateNavigation(menuData));
        }
        return;
    }, [dispatch, sessionData, menuData, isMenuSuccess]);

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
