// import Badge from 'react-bootstrap/Badge';
import { faMinus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Link } from "@components/RouterLink";
import { Button } from "@nautobot/nautobot-ui";
import { calculateLuminance } from "@utils/color";

function TextOrButton({ obj }) {
    if (typeof obj === "object") {
        const display = obj.display || obj.label;
        if (!obj.color) {
            return display;
        }
        // TODO: xs button padding left/right, borderradius and margin should be defaults in nautobot-ui?
        //       also should hover box shadow be disabled?
        return (
            <Button
                size="xs"
                bg={"#" + obj.color}
                color={
                    calculateLuminance(obj.color) > 186 ? "#000000" : "#ffffff"
                }
                borderRadius="sm"
                pl="xs"
                pr="xs"
                m="xs"
            >
                {display}
            </Button>
        );
    }
    return obj;
}

function TableColumnDisplay({ obj }) {
    if (!obj) {
        return <FontAwesomeIcon icon={faMinus} />;
    } else if (typeof obj === "object" && !Array.isArray(obj)) {
        return <TextOrButton obj={obj} />;
    } else if (Array.isArray(obj)) {
        if (typeof obj[0] == "object") {
            return (
                <>
                    {obj.map((item, idx) => (
                        <TextOrButton obj={item} key={idx} />
                    ))}
                </>
            );
        } else {
            return obj.join(", ");
        }
    } else {
        return obj;
    }
}

export default function TableItem({ name, obj, url }) {
    if (url) {
        return (
            <Link to={url}>
                <TableColumnDisplay obj={obj} />
            </Link>
        );
    } else {
        return <TableColumnDisplay obj={obj} />;
    }
}
