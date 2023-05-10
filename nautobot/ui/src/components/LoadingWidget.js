import { Text, StatusIndicator } from "@nautobot/nautobot-ui";
import { Spinner } from "@chakra-ui/react";

// A helpful, consistent loading widget
export function LoadingWidget({ name = "" }) {
    const display_name = name.length > 0 ? " " + name : "";
    return (
        <div style={{ textAlign: "center", width: "100%" }}>
            <StatusIndicator variant="action" breathe={true} />
            <Spinner size="lg" color="blue.500" />
            <Text ml={1}>Loading{display_name}...</Text>
        </div>
    );
}
export default LoadingWidget;
