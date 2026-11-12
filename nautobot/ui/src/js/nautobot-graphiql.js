import { explorerPlugin } from '@graphiql/plugin-explorer';
import { createGraphiQLFetcher } from '@graphiql/toolkit';
import { GraphiQL } from 'graphiql';
import React from 'react';
import ReactDOM from 'react-dom/client';
import 'graphiql/setup-workers/webpack';

import 'graphiql/style.css';
import '@graphiql/plugin-explorer/style.css';

window.GraphiQL = GraphiQL;
window.createGraphiQLFetcher = createGraphiQLFetcher;
window.explorerPlugin = explorerPlugin;
window.React = React;
window.ReactDOM = ReactDOM;
