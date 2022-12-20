import "styles/globals.css"
import "bootstrap/dist/css/bootstrap.css"

const dev = process.env.NODE_ENV !== "production"
export const nautobot_url = dev ? "http://localhost:8080" : ""

function MyApp({ Component, pageProps }) {
  return <Component {...pageProps} />
}

export default MyApp
