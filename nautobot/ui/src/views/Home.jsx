import { Alert } from "@chakra-ui/react"


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
