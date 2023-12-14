import { Flex, Text, Spinner } from "@nautobot/nautobot-ui";

// A helpful, consistent loading widget
export function LoadingWidget({ name = "" }) {
    const display_name = name.length > 0 ? " " + name : "";

    return (
        <Flex align="center" gap="sm" justify="center">
            <Spinner size="lg" color="blue-1" />
            <Text color="gray-3">Loading{display_name}...</Text>
        </Flex>
    );
}
export default LoadingWidget;
