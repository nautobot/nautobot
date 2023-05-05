import {
    NavbarNotificationButton,
    Popover,
    PopoverArrow,
    PopoverBody,
    PopoverContent,
    PopoverTrigger,
    Text,
} from "@nautobot/nautobot-ui";

export default function NotificationPopover({ isLoggedIn, notificatons = [] }) {
    return (
        <Popover>
            <PopoverTrigger>
                <NavbarNotificationButton isDisabled={!isLoggedIn}>
                    {notificatons.length}
                </NavbarNotificationButton>
            </PopoverTrigger>
            <PopoverContent>
                <PopoverArrow />
                <PopoverBody>
                    <Text paddingX="md">No notifications</Text>
                </PopoverBody>
            </PopoverContent>
        </Popover>
    );
}
