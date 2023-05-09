import { Link as UILink } from "@nautobot/nautobot-ui";
import { Link as ReactRouterLink } from "react-router-dom";

// This provides a standard Link object we can use that marries the Link UI component with the ReactRouter Link
export function RouterLink(props) {
    return <UILink as={ReactRouterLink} {...props}></UILink>;
}

export const Link = RouterLink;
export default RouterLink;
