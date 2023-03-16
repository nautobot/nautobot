import { Link } from "@nautobot/nautobot-ui"
import { Link as ReactRouterLink } from "react-router-dom";

export default function RouterLink(props) {

    return (
        <Link as={ReactRouterLink} {...props}></Link>
    )
}