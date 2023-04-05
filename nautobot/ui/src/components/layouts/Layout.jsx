import { Alert } from "@chakra-ui/react";
import {
  Flex,
  Box,
  Sidebar,
  Heading,
  DcimIcon,
  StatusIndicator,
  Text,
  Button
} from "@nautobot/nautobot-ui";
import { Link as ReactRouterLink, useLocation } from "react-router-dom";
import {
  GLOBAL_GRID_GAP,
  GLOBAL_PADDING_RIGHT,
  GLOBAL_PADDING_TOP
} from "@constants/size";
import SidebarNav from "@components/common/SidebarNav";
import RouterLink from "@components/common/RouterLink";
import LoadingWidget from "@components/common/LoadingWidget";

import { useGetSessionQuery, useGetUIMenuQuery } from "@utils/api";
import RouterButton from "@components/common/RouterButton";

export default function Layout({ children }) {
  const location = useLocation();
  const { data: sessionInfo, isSuccess: sessionLoaded } = useGetSessionQuery();
  const { isSuccess: menuLoaded } = useGetUIMenuQuery();

  // TODO: Update for RTK pattern hopefully
  // Here is the safest place to check that the session and menu data are loaded
  // to then regenerate the API and update what is globally known
  // import { useEffect } from "react";
  // const fullApi = generateFullAPI(menuData)
  // useEffect(() => {
  //   updateStore(fullApi)
  // }, [])

  let toRender = children

  if (!sessionLoaded || !menuLoaded || sessionInfo == undefined)
    toRender = <LoadingWidget name="application" />;

  // TODO: This needs to be moved to useEffect. Weird order of operations.
  // const path = location.pathname
  // if (sessionLoaded && !sessionInfo.logged_in && path !== "/")
  //   navigate("/")


  // TODO: This layout can/should be it's own component because we mix component and data calls here
  //   Also, a lot of these styles need to be made globally generic
  //   It would save us the `toRender` above.
  return (
    <Flex direction="column" height="full" overflow="hidden" width="full">
      <Flex flex="1" overflow="hidden" width="full" height="full">
        <Box flex="none" height="100vh" width="var(--chakra-sizes-220)">
          <Sidebar>
            <Heading
              as="h1"
              paddingBottom="md"
              paddingTop="29px"
              paddingX="md"
              color="white"
            >
              <RouterLink to="/">Nautobot</RouterLink>
            </Heading>
            <Heading variant="sidebar">
              <DcimIcon />
              All
            </Heading>
            {sessionInfo && sessionInfo.logged_in ? (
              <>
                <SidebarNav />
                <RouterButton m={3} to="/logout/">Log Out</RouterButton>
              </>
            ) : (
              <RouterButton m={3} to="/login/">Log In</RouterButton>
            )}
          </Sidebar>
        </Box>
        <Box flex="1" overflow="auto">
          <Flex
            direction="column"
            gap={`${GLOBAL_GRID_GAP}px`}
            height="full"
            minWidth="fit-content"
            paddingLeft={`${GLOBAL_GRID_GAP}px`}
            paddingRight={`${GLOBAL_PADDING_RIGHT}px`}
            paddingTop={`${GLOBAL_PADDING_TOP}px`}
          >
            <Flex flex="1" minWidth="fit-content">
              <Box as="main" flex="1" minWidth="fit-content">
                <Alert status="info">
                  <StatusIndicator variant="secondary" breathe={true} />
                  <Text ml={1}>Current route is {location.pathname}</Text>
                </Alert>
                {toRender}
              </Box>
            </Flex>
          </Flex>
        </Box>
      </Flex>
    </Flex>
  );
}
