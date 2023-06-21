// import Badge from 'react-bootstrap/Badge';
import { Link } from "@components/RouterLink";
import { Button, CheckIcon, CloseIcon } from "@nautobot/nautobot-ui";
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
    if (obj === undefined || obj === null || obj === "") {
        return <>&mdash;</>;
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
    } else if (typeof obj === "boolean") {
        if (obj === true) {
            return <CheckIcon />;
        } else {
            return <CloseIcon />;
        }
    } else {
        return obj;
    }
}

export default function ObjectTableItem({ name, obj, url }) {
    if (url && obj) {
        return (
            <Link to={url}>
                <TableColumnDisplay obj={obj} />
            </Link>
        );
    } else {
        return <TableColumnDisplay obj={obj} />;
    }
}
