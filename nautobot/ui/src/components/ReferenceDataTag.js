import { Tag } from "@nautobot/nautobot-ui";
import { Skeleton } from "@chakra-ui/react";
import { useGetRESTAPIQuery } from "@utils/api";
import { calculateLuminance } from "@utils/color";

export function ReferenceDataTag(props) {
    const { model_name, id } = props;
    const { data, isSuccess } = useGetRESTAPIQuery({
        app_label: "extras",
        model_name: model_name,
        uuid: id,
    });

    let display = "Loading...";
    let color = "cccccc";

    if (isSuccess) {
        display = data.display || data.label;
        color = data.color;
    }

    return (
        <Skeleton isLoaded={isSuccess}>
            <Tag
                bg={"#" + color}
                color={calculateLuminance(color) > 186 ? "#000000" : "#ffffff"}
                {...props}
            >
                {display}
            </Tag>
        </Skeleton>
    );
}

export default ReferenceDataTag;
