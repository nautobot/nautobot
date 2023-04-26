// import Badge from 'react-bootstrap/Badge';
import { faMinus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Link } from "react-router-dom";
import { Button } from "@nautobot/nautobot-ui";


const TextOrButton = ({obj}) => {
    if (typeof obj === "object") {
        const display = obj.display || obj.label
        if (!obj.color) {
            return display
        }
        return (
            <Button 
                size="xs"
                className={"ntc-btn-" + obj.color}
            >
                {display}
            </Button>
        )
    }
    return obj

    
}

const TableColumDisplay = ({obj}) => {
    
    if (!obj) {
        return (<FontAwesomeIcon icon={faMinus} />)
    }

    else if (typeof obj === "object"  && !Array.isArray(obj)) {
        return <TextOrButton obj={obj} />
    }

    else if (Array.isArray(obj)) {
        if (typeof obj[0] == "object") {
            return (
                <>
                    {
                        obj.map((item, idx) => <TextOrButton obj={item} key={idx} />)
                    }
                </>
            )
        } else {
            return obj.join(", ");
        }
    }

    else {
        return obj
    }
}


export default function TableItem({ name, obj, url, link = false }) {
    if (link) {
        return <Link to={url}><TableColumDisplay obj={obj} /></Link>
    } else {
        return <TableColumDisplay obj={obj} />;
    }
}
