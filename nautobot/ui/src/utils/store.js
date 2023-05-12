import { configureStore } from "@reduxjs/toolkit";
import { baseApi } from "@utils/api";
import {
    persistReducer,
    FLUSH,
    REHYDRATE,
    PAUSE,
    PERSIST,
    PURGE,
    REGISTER,
} from "redux-persist";
import storage from "redux-persist/lib/storage";
import { combineReducers } from "redux";
import { createSlice } from "@reduxjs/toolkit";

// Configure redux-persist to save state in Local Storage for performance
const persistConfig = {
    key: "root",
    version: 2,
    storage,
};

const initialState = "";

const appContextSlice = createSlice({
    name: "appContext",
    initialState,
    reducers: {
        updateAppContext(state, action) {
            state = action.payload;
            return state;
        },
    },
});

const initialAppState = {
    currentContext: "Inventory", // TODO: What is the context for the homepage?
    routeToContext: {},
    user: {},
    logged_in: false,
    auth: {
        sso_enabled: false,
        backends: [],
    },
};

const appStateSlice = createSlice({
    name: "appState",
    initialState: initialAppState,
    reducers: {
        updateAppCurrentContext(state, action) {
            state.currentContext = action.payload;
            return state;
        },
        updateRouteToContext(state, action) {
            let urlPatternToContext = {};
            let menuInfo = action.payload;
            for (const context in menuInfo) {
                for (const group in menuInfo[context]) {
                    for (const urlPatternOrSubGroupName in menuInfo[context][
                        group
                    ]) {
                        const urlPatternOrSubGroup =
                            menuInfo[context][group][urlPatternOrSubGroupName];
                        if (typeof urlPatternOrSubGroup === "string") {
                            // It's a URL pattern
                            let tokens = urlPatternOrSubGroup.split("/");
                            if (tokens.length === 4) {
                                let appLabel = tokens[1];
                                let modelNamePlural = tokens[2];
                                if (appLabel in urlPatternToContext === false) {
                                    urlPatternToContext[appLabel] = {};
                                }
                                urlPatternToContext[appLabel][modelNamePlural] =
                                    context;
                            }
                        } else {
                            // It's a submenu
                            for (const urlPattern in urlPatternOrSubGroup) {
                                let tokens = urlPattern.split("/");
                                if (tokens.length === 4) {
                                    let appLabel = tokens[1];
                                    let modelNamePlural = tokens[2];
                                    if (
                                        appLabel in urlPatternToContext ===
                                        false
                                    ) {
                                        urlPatternToContext[appLabel] = {};
                                    }
                                    urlPatternToContext[appLabel][
                                        modelNamePlural
                                    ] = context;
                                }
                            }
                        }
                    }
                }
            }

            state.routeToContext = urlPatternToContext;
            return state;
        },
        updateSessionState(state, action) {
            state.user = action.payload.user;
            state.logged_in = action.payload.logged_in;
            state.auth = state.auth || {};
            state.auth.sso_enabled = action.payload.sso_enabled;
            state.auth.backends = action.payload.backends;
            return state;
        },
        flushSessionState(state, action) {
            state.user = {};
            state.logged_in = false;
        },
    },
});

export function getCurrentAppContextSelector(app_label, model_name) {
    return (store) => {
        return (
            store?.appState?.routeToContext[app_label]?.[model_name] ||
            "Inventory"
        );
    };
}

export function isLoggedInSelector(state) {
    return state?.appState?.logged_in || false;
}

const rootReducer = combineReducers({
    [baseApi.reducerPath]: baseApi.reducer,
    appContext: appContextSlice.reducer,
    appState: appStateSlice.reducer,
});

// Instantiate the persistent reducer to pull state from cache
const persistedReducer = persistReducer(persistConfig, rootReducer);

export const { updateAppContext } = appContextSlice.actions;
export const {
    updateAppCurrentContext,
    updateRouteToContext,
    updateSessionState,
    flushSessionState,
} = appStateSlice.actions;

// Global Redux store for global state management
export const store = configureStore({
    reducer: persistedReducer,
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware({
            serializableCheck: {
                ignoredActions: [
                    FLUSH,
                    REHYDRATE,
                    PAUSE,
                    PERSIST,
                    PURGE,
                    REGISTER,
                ],
            },
        }).concat(baseApi.middleware),
});

// TODO: This was a pattern to allow the dynamic store updates but doesn't seem to be working
// at the moment. Could just be a component issue.
// import dynamicMiddlewares from 'redux-dynamic-middlewares'
// import { addMiddleware } from 'redux-dynamic-middlewares'

// export const persistConfig = {
//   key: 'root',
//   version: 1,
//   storage,
// }

// export const rootReducer = combineReducers({
//   session: sessionReducer,
//   [apiSlice.reducerPath]: apiSlice.reducer,
// })

// export const persistedReducer = persistReducer(persistConfig, rootReducer)

// export const store = configureStore({
//   reducer: persistedReducer,
//   middleware: getDefaultMiddleware => getDefaultMiddleware({
//     serializableCheck: {
//       ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER],
//     },
//   }).concat(dynamicMiddlewares)
// });

// addMiddleware(apiSlice.middleware)
