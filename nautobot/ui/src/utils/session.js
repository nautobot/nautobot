// TODO: This file may go away entirely with the RTK Query pattern
import axios from "axios";
import { API_USER_SESSION_INFO } from "@constants/apiPath";
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

export function getSession() {}

export function setSession(session_object) {}

export const fetchSessionAsync = createAsyncThunk(
    "session/fetchSession",
    async () => {
        const response = await axios.get(API_USER_SESSION_INFO);
        // The value we return becomes the `fulfilled` action payload
        return response.data;
    }
);

const initialState = {
    logged_in: false,
    userinfo: {
        display: "Anonymous",
    },
    status: "starting",
    backends: [],
    sso_enabled: false,
    sso_user: false,
};

function decomposeSessionToState(state, payload) {
    state.userinfo = payload.user;
    state.logged_in = payload.logged_in;
    state.sso_enabled = payload.sso_enabled;
    state.sso_user = payload.sso_user;
}

export const sessionSlice = createSlice({
    name: "session",
    initialState,
    reducers: {
        login: (state, action) => {
            decomposeSessionToState(state, action.payload);
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchSessionAsync.pending, (state) => {
                state.status = "loading";
            })
            .addCase(fetchSessionAsync.fulfilled, (state, action) => {
                state.status = "idle";
                decomposeSessionToState(state, action);
            });
    },
});

const { actions, reducer } = sessionSlice;

export const selectLoggedIn = (state) => state.session.logged_in;
export const selectUsername = (state) =>
    (state.session.userinfo && state.session.userinfo.display) || "";

export const { login } = actions;
export default reducer;
