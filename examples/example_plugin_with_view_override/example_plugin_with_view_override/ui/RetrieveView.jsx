import { Box } from '@nautobot/nautobot-ui';
import GenericView from "@views/generic/GenericView";

export function RetrieveView(props) {
    return (
        <GenericView>
            <Box>
                I am a full-fledge view provided by the default example App.
                The ID of the object I am displaying is: {props.id}
            </Box>
        </GenericView>
    );
}

export default RetrieveView;
