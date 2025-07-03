'use strict';

import { fetch } from 'whatwg-fetch';
import { render } from 'react-dom';
import { GraphiQL } from 'graphiql';
import { createGraphiQLFetcher } from '@graphiql/toolkit';
import * as GraphiQLPluginExplorer from '@graphiql/plugin-explorer';
import * as graphqlWs from 'graphql-ws';
import React from 'react';
import ReactDOM from 'react-dom';

import 'graphiql/graphiql.css';
import '@graphiql/plugin-explorer/dist/style.css';

GraphiQL.createFetcher = createGraphiQLFetcher;

window.fetch = fetch;
window.graphqlWs = graphqlWs;
window.GraphiQL = GraphiQL;
window.GraphiQLPluginExplorer = GraphiQLPluginExplorer;
window.React = React;
window.ReactDOM = ReactDOM;
