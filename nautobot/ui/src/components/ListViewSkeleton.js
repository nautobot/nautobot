import { SkeletonText, SkeletonCircle } from "@chakra-ui/react";
import { NautobotGridItem } from "@nautobot/nautobot-ui";

export function ListViewSkeleton({ model_name = "", page_size = "10" }) {
    return (
        <NautobotGridItem colSpan={3}>
            <h1>Loading {model_name} ...</h1>
            <SkeletonCircle size="45" endColor="gray.300"></SkeletonCircle>
            <SkeletonText
                endColor="gray.300"
                noOfLines={parseInt(page_size)}
                skeletonHeight="30"
                spacing="6"
                mt="6"
            ></SkeletonText>
        </NautobotGridItem>
    );
}

export default ListViewSkeleton;
