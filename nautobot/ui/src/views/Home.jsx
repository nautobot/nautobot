import { Alert } from "@chakra-ui/react"  // TODO: import from nautobot-ui when available


export default function Home({ children }) {
  return (
    <>
      <Alert status="success">
        Hello from React! 👋 <br />
      </Alert>
      {children}
    </>
  )
}
