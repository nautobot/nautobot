import {BiHome, BiCog, BiBookContent} from "react-icons/bi";
import {Link} from "react-router-dom";
import {Button} from "@chakra-ui/react";

export default function LinkedIcon({icon, link, tooltip}) {
    const common_props = {
        size: 15,
    }

    const renderIcon = (data) => {
        switch (data){
            case "home":
                return <Button  colorScheme='blue' variant='solid' size="xs" leftIcon={<BiHome {...common_props} />} iconSpacing={0} />
            case "cog":
                return <Button  colorScheme='orange' variant='solid' size="xs" leftIcon={<BiCog {...common_props} />} iconSpacing={0} />
            case "book":
                return <Button  colorScheme='teal' variant='solid' size="xs" leftIcon={<BiBookContent {...common_props} />} iconSpacing={0} />
            default:
                return <BiHome />
        }
    }

    return (
            <Link to="#">
                {renderIcon(icon)}
            </Link>
    )
}
