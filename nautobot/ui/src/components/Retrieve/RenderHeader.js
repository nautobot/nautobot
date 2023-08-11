import { faCalendarPlus, faPencil } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    BinIcon,
    Box,
    Button as UIButton,
    ButtonGroup,
    EditIcon,
    Heading,
    MeatballsIcon,
    Menu,
    MenuButton,
    MenuList,
    MenuItem,
    NtcThumbnailIcon,
    Text,
} from "@nautobot/nautobot-ui";

import { ReferenceDataTag } from "@components/ReferenceDataTag";
import { humanFriendlyDate } from "@utils/date";

export default function RenderHeader({ data }) {
    return (
        <Box display="flex" justifyContent="space-between" padding="md">
            <Heading display="flex" alignItems="center" gap="5px">
                {/* TODO(Timizuo): Create a reusable component from <Heading><NtcThumbnailIcon /> {title}</Heading> */}
                <NtcThumbnailIcon width="25px" height="30px" />{" "}
                <Text size="H1" as="h1">
                    {data.display}
                </Text>
                {data.status && (
                    <Box p={2} flexGrow="1">
                        <Text size="P2">
                            <ReferenceDataTag
                                model_name="statuses"
                                id={data.status.id}
                                variant="unknown"
                                size="sm"
                            />
                        </Text>
                    </Box>
                )}
                {data.created && (
                    <Box p={2} flexGrow="1">
                        <Text size="P2" color="gray-2">
                            <FontAwesomeIcon icon={faCalendarPlus} />
                            {humanFriendlyDate(data.created)}
                        </Text>
                    </Box>
                )}
                {data.last_updated && (
                    <Box p={2} flexGrow="1">
                        <Text size="P2" color="gray-2">
                            <FontAwesomeIcon icon={faPencil} />
                            {humanFriendlyDate(data.last_updated)}
                        </Text>
                    </Box>
                )}
            </Heading>
            <ButtonGroup alignItems="center">
                <Menu>
                    <MenuButton
                        as={UIButton}
                        size="sm"
                        variant="primaryAction"
                        leftIcon={<MeatballsIcon />}
                    >
                        Actions
                    </MenuButton>
                    <MenuList>
                        <MenuItem
                            to={`${window.location.pathname}edit/`}
                            icon={<EditIcon />}
                            onClick={(e) => {
                                e.preventDefault();
                                // Because there is currently no support for Edit view in the new UI for production,
                                // the code below checks if the app is running in production and redirects the user to
                                // the Edit page; after the page is reloaded, nautobot takes care of rendering the legacy UI.
                                // TODO: Get rid of this if statement when we have a Create/Update View in the new UI
                                if (process.env.NODE_ENV === "production") {
                                    document.location.href += "edit/";
                                }
                            }}
                        >
                            {" "}
                            Edit
                        </MenuItem>
                        <MenuItem
                            to={`${window.location.pathname}delete/`}
                            icon={<BinIcon />}
                            onClick={(e) => {
                                e.preventDefault();
                                // Because there is currently no support for Delete view in the new UI for production,
                                // the code below checks if the app is running in production and redirects the user to
                                // the Delete page; after the page is reloaded, nautobot takes care of rendering the legacy UI.
                                // TODO: Get rid of this if statement when we have a Delete View in the new UI
                                if (process.env.NODE_ENV === "production") {
                                    document.location.href += "delete/";
                                }
                            }}
                        >
                            {" "}
                            Delete
                        </MenuItem>
                    </MenuList>
                </Menu>
            </ButtonGroup>
        </Box>
    );
}
