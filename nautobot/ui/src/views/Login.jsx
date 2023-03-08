import { Button, FormControl, FormLabel, Input } from "@nautobot/nautobot-ui"
import { Card, CardHeader, CardBody, CardFooter } from "@chakra-ui/react"
import axios from "axios"


export default function Login() {
  const handleSubmit = (e) => {
    e.preventDefault();
    axios.post(
      '/api/users/tokens/authenticate/', {
        username: e.target.username.value,
        password: e.target.password.value,
      })
      .then(() => {
        localStorage.setItem("nautobot-user", e.target.username.value)
        window.location.replace("/")
      })
      .catch(err => alert(err.detail))
  }
  return (
      <Card>
        <form method="POST" onSubmit={handleSubmit}>
            <CardHeader>Log In</CardHeader>
            <CardBody>
              <FormControl>
                <FormLabel>Username</FormLabel>
                <Input isRequired={true} name="username"></Input>
              </FormControl>
              <FormControl>
                <FormLabel>Password</FormLabel>
                <Input isRequired={true} name="password" type="password"></Input>
              </FormControl>
            </CardBody>
            <CardFooter>
              <Button type="submit">Log In</Button>
            </CardFooter>
        </form>
      </Card>
  )
}
