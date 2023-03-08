import { Flex, Box, Link, Button } from "@nautobot/nautobot-ui"
import { Spacer, Image, Menu, MenuButton, MenuDivider, MenuList, MenuGroup, MenuItem } from "@chakra-ui/react"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSignIn, faSignOut } from "@fortawesome/free-solid-svg-icons";
import { Fragment } from "react"
import { NavLink, redirect, useNavigate} from "react-router-dom"
import {useState, useEffect} from "react"
import useSWR from "swr"
import axios from "axios";


const fetcher = (url) => fetch(url, { credentials: "include" }).then((res) => res.json());

export default function BSNavBar() {
  const navigate = useNavigate();

  const { data, error } = useSWR("/api/ui/get-menu/", fetcher)
  const [ isLoggedIn, setIsLoggedIn] = useState(false)
  useEffect(() => {
    // Check if `nautobot-user` exist in localStorage; if found set setIsLoggedIn to true else false
    setIsLoggedIn(localStorage.getItem("nautobot-user") != null)
  }, [])

  const logout = () => {
    axios.get("/api/users/tokens/logout/")
    setIsLoggedIn(false)
    localStorage.removeItem("nautobot-user")
    navigate("/login")
  }
  if (error) return <div>Failed to load menu</div>
  if (!data) return <></>


  return (
    <Flex minWidth="max-content">
      <Link href="/">
        <Image src="/static/img/nautobot_logo.svg" alt="nautobot-logo" height={30} htmlHeight={30}/>
      </Link>
      {
        data.map((item, idx) => (
          <Menu key={idx}>
            <MenuButton>
              {item.name}
            </MenuButton>
            <MenuList>
              {
                Object.entries(item.properties.groups).map((group, group_idx) => (
                  <Fragment key={group_idx}>
                    <MenuGroup title={group[0]}>
                      {
                        Object.entries(group[1].items).map((menu, menu_idx) => (
                          <MenuItem as="a" href={menu[0]} key={menu_idx}>{menu[1].name}</MenuItem>
                        ))
                      }
                    </MenuGroup>
                    <MenuDivider/>
                  </Fragment>
                ))
              }
            </MenuList>
          </Menu>
        ))
      }
      <Spacer/>
        {
            isLoggedIn ?
                <span role="button" className="border-0 btn-success cusor-pointer" onClick={() => logout()}>
                  <FontAwesomeIcon icon={faSignOut} />
                  {" Logout"}
                </span>
            :
                <Link href="/login/">
                  <FontAwesomeIcon icon={faSignIn} />
                  {" Login"}
                </Link>
        }
    </Flex>
  )
}
