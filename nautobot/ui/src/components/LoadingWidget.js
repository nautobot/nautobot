import { Text, StatusIndicator } from "@nautobot/nautobot-ui";
import { Spinner } from "@chakra-ui/react";

// A helpful, consistent loading widget
export function LoadingWidget({ name = "" }) {
    const display_name = name.length > 0 ? " " + name : "";
    return (
        <div style={{ textAlign: "center", position: "relative", top: "40%", gridColumn: "2 / span 2" }}>
            <StatusIndicator variant="action" breathe={true} />
            <Spinner size="lg" color="blue.500" />
            <Text ml={1} color="gray-3">Loading{display_name}...</Text>
        </div>
    );
}
export default LoadingWidget;
