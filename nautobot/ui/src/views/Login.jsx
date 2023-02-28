import { Button } from "@nautobot/nautobot-ui"
import { Card, CardHeader, CardBody, CardFooter, FormControl, FormLabel, Input } from "@chakra-ui/react"
import Cookies from "js-cookie"


export default function Login() {
  const csrf_token = Cookies.get("csrftoken")
  return (
      <Card>
        <form action="/login/" method="POST">
            <CardHeader>Log In</CardHeader>
            <CardBody>
              <input type="hidden" name="csrfmiddlewaretoken" value={csrf_token}/>
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
