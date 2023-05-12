import { Text } from "@nautobot/nautobot-ui";
import spinningNautobot from "../assets/spinning-nautobot.gif";

// A helpful, consistent loading widget
export function LoadingWidget({ name = "" }) {
    const display_name = name.length > 0 ? " " + name : "";
    return (
        <div
            style={{
                textAlign: "center",
                width: "100%",
                position: "relative",
                top: "40%",
            }}
        >
            <img
                src={spinningNautobot}
                alt="spinning-nautobot"
                style={{ marginLeft: "auto", marginRight: "auto" }}
            />
            <Text color="gray.500">Loading{display_name}...</Text>
        </div>
    );
}
export default LoadingWidget;
