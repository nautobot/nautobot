import React from 'react';
import { BrowserRouter } from "react-router-dom"
import { NautobotUIProvider } from "@nautobot/nautobot-ui"

import Layout from '@components/layouts/Layout';
import NautobotRouter from "src/router"


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
