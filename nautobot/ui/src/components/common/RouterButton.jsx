import { Button as UIButton } from "@nautobot/nautobot-ui";
import { Link as ReactRouterLink } from "react-router-dom";

// This provides a standard Link object we can use that marries the Button UI component with the ReactRouter Link
export function RouterButton(props) {
    return <UIButton as={ReactRouterLink} {...props}></UIButton>;
}

export const Button = RouterButton;
export default RouterButton;
