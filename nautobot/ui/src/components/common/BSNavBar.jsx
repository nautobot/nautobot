import { Flex, Box, Spacer, Image, Link, Menu, MenuButton, MenuDivider, MenuList, MenuGroup, MenuItem } from "@chakra-ui/react"
import { faRightToBracket } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Fragment } from "react"
import { NavLink } from "react-router-dom"
import useSWR from "swr"


const fetcher = (url) => fetch(url, { credentials: "include" }).then((res) => res.json());

export default function BSNavBar() {
  const { data, error } = useSWR("/api/get-menu/", fetcher)
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
      <Link href="/login/">Login</Link>
    </Flex>
  )
}
