import { Flex, Box, Link, Button } from "@nautobot/nautobot-ui"
import { Spacer, Image, Menu, MenuButton, MenuDivider, MenuList, MenuGroup, MenuItem } from "@chakra-ui/react"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSignIn, faSignOut } from "@fortawesome/free-solid-svg-icons";
import { Fragment } from "react"
import RouterLink from "@components/common/RouterLink"

import { useGetSessionQuery, useGetUIMenuQuery } from "@utils/apiSlice";


export default function BSNavBar() {
  const { data: sessionInfo, isLoading, isSuccess, isError } = useGetSessionQuery();
  const { data: menuInfo, isLoading: isMenuLoading, isSuccess: isMenuSuccess, isError: isMenuError } = useGetUIMenuQuery();

  const logout = () => {}
  if (isMenuError) return <div>Failed to load menu</div>
  if (!isMenuSuccess) return <></>


  return (
    <Flex minWidth="max-content">
      <Link href="/">
        <Image src="/static/img/nautobot_logo.svg" alt="nautobot-logo" height={30} htmlHeight={30}/>
      </Link>
      {
        menuInfo.map((item, idx) => (
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
            isLoading ?
                <span>Loading user session...</span>
            : isSuccess ?
                <span>{sessionInfo.user.display}</span>
            : 
              <span>Error</span>
        }
      <Spacer/>
        {
            isSuccess && sessionInfo.logged_in ?
                <span role="button" className="border-0 btn-success cusor-pointer" onClick={() => logout()}>
                  <FontAwesomeIcon icon={faSignOut} />
                  {" Logout"}
                </span>
            :
                <RouterLink to="/log_in/">
                  <FontAwesomeIcon icon={faSignIn} />
                  {" Login"}
                </RouterLink>
        }
    </Flex>
  )
}
