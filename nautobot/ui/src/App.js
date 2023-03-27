import React from 'react';
import { BrowserRouter } from "react-router-dom"
import { NautobotUIProvider } from "@nautobot/nautobot-ui"

import Layout from '@components/layouts/Layout';
import NautobotRouter from "src/router"

// TODO: See if we can/need to continue this pattern:
// Global API pattern needs these arguments passed through:
//   { updateStore, globalApi }
// (see index.js for context)

function App() {
  return (
    <NautobotUIProvider>
      <BrowserRouter>
        <Layout>
          <NautobotRouter />
        </Layout>
      </BrowserRouter>
    </NautobotUIProvider>
  );
}

export default App;
