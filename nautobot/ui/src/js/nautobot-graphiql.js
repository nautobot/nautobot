import { explorerPlugin } from '@graphiql/plugin-explorer';
import { useGraphiQLActions, GraphiQLProvider } from '@graphiql/react';
import { createGraphiQLFetcher } from '@graphiql/toolkit';
import { GraphiQL } from 'graphiql';
import React from 'react';
import ReactDOM from 'react-dom/client';
import 'graphiql/setup-workers/webpack';

import 'graphiql/style.css';
import '@graphiql/plugin-explorer/style.css';

window.graphiql ??= {};

window.graphiql.GraphiQL = GraphiQL;
window.graphiql.GraphiQLProvider = GraphiQLProvider;
window.graphiql.createGraphiQLFetcher = createGraphiQLFetcher;
window.graphiql.explorerPlugin = explorerPlugin;
window.graphiql.React = React;
window.graphiql.ReactDOM = ReactDOM;
window.graphiql.useGraphiQLActions = useGraphiQLActions;
