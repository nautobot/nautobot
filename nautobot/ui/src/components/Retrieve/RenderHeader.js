import { faCalendarPlus, faPencil } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    BinIcon,
    Button as UIButton,
    ButtonGroup,
    Divider,
    EditIcon,
    Flex,
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
        <Flex justify="space-between">
            <Flex align="center" gap="md">
                {/* TODO(Timizuo): Create a reusable component from <Heading><NtcThumbnailIcon /> {title}</Heading> */}
                <Heading
                    alignItems="center"
                    as="h1"
                    display="flex"
                    gap="xs"
                    size="H1"
                >
                    <NtcThumbnailIcon height="auto" width="24" />
                    {data.display}
                </Heading>
                {data.status && (
                    <Text size="P2">
                        <ReferenceDataTag
                            model_name="statuses"
                            id={data.status.id}
                            variant="unknown"
                            size="sm"
                        />
                    </Text>
                )}
                <Divider height={10} orientation="vertical" />
                {data.created && (
                    <Text
                        alignItems="center"
                        color="gray-3"
                        display="flex"
                        gap="xs"
                    >
                        <FontAwesomeIcon
                            icon={faCalendarPlus}
                            style={{ height: 20, width: 20 }}
                        />
                        {humanFriendlyDate(data.created)}
                    </Text>
                )}
                {data.last_updated && (
                    <Text
                        alignItems="center"
                        color="gray-3"
                        display="flex"
                        gap="xs"
                    >
                        <FontAwesomeIcon
                            icon={faPencil}
                            style={{ height: 20, width: 20 }}
                        />
                        {humanFriendlyDate(data.last_updated)}
                    </Text>
                )}
            </Flex>
            <ButtonGroup alignItems="center" spacing="md">
                <Menu>
                    <MenuButton
                        as={UIButton}
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
                            Delete
                        </MenuItem>
                    </MenuList>
                </Menu>
            </ButtonGroup>
        </Flex>
    );
}
