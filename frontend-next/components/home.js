import Alert from "react-bootstrap/Alert"

export default function Home({ children }) {
  return (
    <>
      <Alert variant="success" style={{ textAlign: "center" }}>
        Example Plugin says “Hello, admin!” 👋 <br />
      </Alert>
      {children}
    </>
  )
}
