import { Text, StatusIndicator } from "@nautobot/nautobot-ui";

// A helpful, consistent loading widget
export function LoadingWidget({ name = "" }) {
    const display_name = name.length > 0 ? " " + name : "";
    return (
        <div>
            <StatusIndicator variant="action" breathe={true} />
            <Text ml={1}>Loading{display_name}...</Text>
        </div>
    );
}
export default LoadingWidget;
