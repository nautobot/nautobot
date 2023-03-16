import { Alert } from "@chakra-ui/react";
import { Flex, Box, Sidebar, Heading, DcimIcon, StatusIndicator, Text, Button } from "@nautobot/nautobot-ui";
import { useLocation } from "react-router-dom";
import { GLOBAL_GRID_GAP, GLOBAL_PADDING_RIGHT, GLOBAL_PADDING_TOP } from "@constants/size";
import SidebarNav from "@components/common/SidebarNav";
import RouterLink from "@components/common/RouterLink";

import { useGetSessionQuery } from "@utils/apiSlice";

export default function Layout({ children }) {
  let location = useLocation();
  const { data: sessionInfo, isLoading: sessionLoading, isSuccess: sessionLoaded, isError } = useGetSessionQuery();

  if (!sessionLoaded) return <Alert status='info'>
  <StatusIndicator
variant="info"
breathe={true}
/><Text ml={1}>Loading</Text>
  </Alert>
  return (
    <Flex
      direction="column"
      height="full"
      overflow="hidden"
      width="full"
    >

      <Flex flex="1" overflow="hidden" width="full" height="full">
        <Box
          flex="none"
          height="100vh"
          width="var(--chakra-sizes-220)"
        >
          <Sidebar>
            <Heading as="h1" paddingBottom="md"
      paddingTop="29px"
      paddingX="md" color="white">Nautobot</Heading>
            <Heading variant="sidebar">
              <DcimIcon />
              All
            </Heading>

            { sessionInfo.logged_in ? <SidebarNav /> : <Button m={3}><RouterLink to="/login/">Log In</RouterLink></Button>}
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
                <Alert status='info'>
                <StatusIndicator
      variant="success"
      breathe={true}
    /><Text ml={1}>Current route is {location.pathname}</Text>
                </Alert>
                {children}
              </Box>
            </Flex>
          </Flex>
        </Box>
      </Flex>
    </Flex>
  );
}
