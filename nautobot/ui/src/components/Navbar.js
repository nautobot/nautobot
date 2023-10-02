import { useEffect, useMemo } from "react";
import { useSelector } from "react-redux";
import {
    Link as ReactRouterLink,
    NavLink as ReactRouterNavLink,
    useLocation,
    useSearchParams,
    useParams,
    useNavigate,
} from "react-router-dom";
import debounce from "lodash.debounce";

import {
    AutomationIcon,
    DcimIcon,
    Input,
    InputGroup,
    InputLeftElement,
    IpamIcon,
    Menu,
    MenuButton,
    MenuItem,
    MenuList,
    Navbar as UINavbar,
    NavbarMenuButton,
    NavbarSection,
    NavbarSections,
    PlatformIcon,
    SearchIcon,
    SecurityIcon,
    Tooltip,
} from "@nautobot/nautobot-ui";

import RouterButton from "@components/RouterButton";
import { FILTER_RESET_QUERY_PARAMS } from "./FiltersPanel";
import { useGetNewUIReadyRoutesQuery } from "@utils/api";
import { isRouteNewUIReady } from "@utils/navigation";
import {
    currentUserSelector,
    isLoggedInSelector,
    getCurrentContextSelector,
} from "@utils/store";

export function Navbar() {
    const isLoggedIn = useSelector(isLoggedInSelector);
    const currentContext = useSelector(getCurrentContextSelector);
    const currentUser = useSelector(currentUserSelector);
    const { app_label, model_name, object_id } = useParams(); // For use in determining if user is on a list or detail view, or neither
    const location = useLocation();
    const navigate = useNavigate(); // For use in navigating to the list view with the search params in the URL
    const { data: readyRoutes } = useGetNewUIReadyRoutesQuery();
    const isListOrDetailView = Boolean(app_label && model_name);

    const [searchParams, setSearchParams] = useSearchParams();

    const debouncedOnChangeSearchBox = useMemo(() => {
        /**
         * Debounce the search box change handler to prevent excessive API calls.
         *
         * This will wait until the user has stopped typing for 300ms before
         * calling the change handler.
         *
         * If the user is on a list view, the search params will be updated in the URL
         * and the user will be navigated to the new URL.
         *
         * If the user is on a detail view, the user will be navigated to the list view
         * with the search params in the URL.
         */
        const changeHandler = (event) => {
            if (object_id) {
                navigate(
                    `/${app_label}/${model_name}/?${new URLSearchParams([
                        ["q", event.target.value],
                    ])}`
                );
            } else {
                const filters = event.target.value
                    ? [["q", event.target.value]]
                    : [];
                setSearchParams([
                    ...filters,
                    ...[...searchParams].filter(
                        ([searchParamLabel]) =>
                            !FILTER_RESET_QUERY_PARAMS.includes(
                                searchParamLabel
                            ) && searchParamLabel !== "q"
                    ),
                ]);
            }
        };
        return debounce(changeHandler, 300);
    }, [
        searchParams,
        setSearchParams,
        app_label,
        model_name,
        object_id,
        navigate,
    ]);

    const SearchBox = (
        <Input
            placeholder="Search..."
            defaultValue={searchParams.get("q")}
            onChange={debouncedOnChangeSearchBox}
            disabled={!isListOrDetailView} // Disable search box if not on a list or detail view (global search is not yet implemented)
        />
    );

    // Check if current location is NewUIReady; if not redirect user back to legacy UI
    useEffect(() => {
        if (readyRoutes) {
            // Remove trailing `/`, as `isRouteNewUIReady` requires this.
            const path = location.pathname.replace(/^\/+/, "");
            if (!isRouteNewUIReady(path, readyRoutes)) {
                window.location.reload();
            }
        }
    }, [location, readyRoutes]);

    return (
        <UINavbar>
            <NavbarSections>
                {[
                    {
                        children: "Inventory",
                        leftIcon: <DcimIcon />,
                        to: "/dcim/devices/",
                    },
                    {
                        children: "Networks",
                        leftIcon: <IpamIcon />,
                        to: "/ipam/prefixes/",
                    },
                    {
                        children: "Security",
                        leftIcon: <SecurityIcon />,
                        to: "/extras/secrets/",
                    },
                    {
                        children: "Automation",
                        leftIcon: <AutomationIcon />,
                        to: "/extras/jobs/",
                    },
                    {
                        children: "Platform",
                        leftIcon: <PlatformIcon />,
                        to: "/extras/relationships/",
                    },
                ].map(({ children, to, ...rest }) => (
                    <ReactRouterNavLink key={to} to={to}>
                        {({ isActive }) => (
                            <NavbarSection
                                as="button"
                                isActive={
                                    isActive || children === currentContext
                                }
                                children={children}
                                {...rest}
                            />
                        )}
                    </ReactRouterNavLink>
                ))}
            </NavbarSections>
            <Tooltip
                label="Global search is not yet implemented."
                placement="bottom"
                isDisabled={isListOrDetailView} // Disable tooltip if on a list or detail view (contextual search is implemented)
            >
                <InputGroup flex="1" size="lg" variant="navbar">
                    <InputLeftElement>
                        <SearchIcon />
                    </InputLeftElement>
                    {SearchBox}
                </InputGroup>
            </Tooltip>
            {!isLoggedIn && <RouterButton to="/login/">Log In</RouterButton>}
            {isLoggedIn && (
                <Menu>
                    <MenuButton as={NavbarMenuButton} isDisabled={!isLoggedIn}>
                        {currentUser?.display || currentUser?.username}
                    </MenuButton>
                    <MenuList>
                        {[
                            {
                                children: "Log Out",
                                color: "red-1",
                                to: "/logout",
                            },
                        ].map(({ to, ...rest }) => (
                            <MenuItem
                                key={to}
                                as={ReactRouterLink}
                                to={to}
                                {...rest}
                            />
                        ))}
                    </MenuList>
                </Menu>
            )}
        </UINavbar>
    );
}
export default Navbar;
