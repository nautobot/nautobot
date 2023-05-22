import { configureStore } from "@reduxjs/toolkit";
import { baseApi } from "@utils/api";
import { combineReducers } from "redux";
import { createSlice } from "@reduxjs/toolkit";
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

//
// Auth
//

const initialAuthState = {
    logged_in: false,
    user: {},
    sso_enabled: false,
    backends: [],
};

/**
 * Redux slice for logged_in state
 * @param {Object} state - The current state
 * @returns {boolean} - Whether the user is logged in
 */
export function isLoggedInSelector(state) {
    return state?.appState?.auth?.logged_in || false;
}

/**
 * Redux slice for current user state
 * @param {Object} state - The current state
 * @returns {Object} - Whether the user is logged in
 */
export function currentUserSelector(state) {
    return state?.appState?.auth?.user || {};
}

//
// Navigation
//

const initialCurrentContext = "Inventory";

const initialNavigationState = {
    currentContext: initialCurrentContext, // TODO: Add sidebar support for null
    contextToRoute: {},
    routeToContext: {},
};

/**
 * Given an App Label and Model Name, return the current context
 * @param {string} app_label
 * @param {string} model_name
 * @returns {string} The current context
 */
export function getCurrentAppContextSelector(app_label, model_name) {
    return (store) => {
        return (
            store?.appState?.navigation?.routeToContext[app_label]?.[
                model_name
            ] || initialCurrentContext
        );
        // TODO: We should probably throw an error or not fall back to Inventory if the context is not found
    };
}
/**
 *
 * @param {Object} state - The current state
 * @returns
 */
export function getCurrentContextSelector(state) {
    return state?.appState?.navigation?.currentContext || initialCurrentContext;
}

/**
 * Retrieve the contextToRoute object from the application state
 * @param {Object} state
 * @returns {Object} The navigation slice of the application state
 */
export function getMenuInfoSelector(state) {
    return state?.appState?.navigation?.contextToRoute || {};
}

//
// App State
//

const initialAppState = {
    auth: structuredClone(initialAuthState),
    navigation: structuredClone(initialNavigationState),
};

const appStateSlice = createSlice({
    name: "appState",
    initialState: initialAppState,
    reducers: {
        /**
         * Updates the current context of the app
         * @param {Object} state - The current state
         * @param {Object} action - The called-with payload, which should be one of the keys in the contextToRoute object
         * @returns
         */
        updateCurrentContext(state, action) {
            // TODO: Add validation that the payload is a valid context
            state.navigation.currentContext = action.payload;
            return state;
        },
        /**
         * Given an API payload with the menu information store both directions of menu
         * - Context (Inventory, Circuits, etc) to Route (app/model) (contextToRoute)
         * - Route (app/model) to Context (Inventory, Circuits, etc) (routeToContext)
         * @param {Object} state - The current state
         * @param {Object} action - The called-with payload (from the API)
         * @returns The updated state
         */
        updateNavigation(state, action) {
            let menuInfo = action.payload;
            state.navigation =
                state.navigation || structuredClone(initialNavigationState);
            state.navigation.contextToRoute = menuInfo;
            let urlPatternToContext = {};
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

            state.navigation.routeToContext = urlPatternToContext;
            return state;
        },
        /**
         * Given an API payload with session information, updates the state with the session information
         * @param {Object} state - The current state
         * @param {Object} action - The called-with payload and action type
         * @returns The updated state
         */
        updateAuthStateWithSession(state, action) {
            state.auth = state.auth || structuredClone(initialAuthState);
            state.auth.user = action.payload.user;
            state.auth.logged_in = action.payload.logged_in;
            state.auth.sso_enabled = action.payload.sso_enabled;
            state.auth.backends = action.payload.backends;
            return state;
        },
        /**
         * Set the user back to logged-out and clear the user object
         * @param {Object} state - The current state
         * @param {*} _ - The called-with payload, ignored here
         * @returns The updated state
         */
        flushSessionState(state, _) {
            state.auth.user = {};
            state.auth.logged_in = false;
            return state;
        },
    },
});

// The actions available to update the App State slice
export const {
    updateCurrentContext,
    updateNavigation,
    updateAuthStateWithSession,
    flushSessionState,
} = appStateSlice.actions;

// Combine our internal app state reducers with the RTK Query reducers
const rootReducer = combineReducers({
    [baseApi.reducerPath]: baseApi.reducer,
    appState: appStateSlice.reducer,
});

// Configure redux-persist to save state in Local Storage for performance
const persistConfig = {
    key: "root",
    version: 3, // Increment this number if you change the shape of the state
    storage,
};

// Instantiate the persistent reducer to pull state from cache
const persistedReducer = persistReducer(persistConfig, rootReducer);

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
