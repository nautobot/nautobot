'use strict'

import { fetch } from 'whatwg-fetch';
import GraphiQL from 'graphiql';
import React from 'react';
import ReactDOM from 'react-dom';
import * as SubscriptionsTransportWs from 'subscriptions-transport-ws';

import 'graphiql/graphiql.css';

window.fetch = fetch;
window.GraphiQL = GraphiQL;
window.React = React;
window.ReactDOM = ReactDOM;
window.SubscriptionsTransportWs = SubscriptionsTransportWs;
