import Alert from "react-bootstrap/Alert"

export default function Home({ children }) {


  return (
    <>
      <Alert variant="success" style={{ textAlign: "center" }}>
        Hello from React! 👋 <br />
      </Alert>
      {children}
    </>
  )
}
