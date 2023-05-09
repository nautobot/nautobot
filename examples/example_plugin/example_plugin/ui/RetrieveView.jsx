import { Card } from '@chakra-ui/react';
import GenericView from "@views/generic/GenericView";

export function RetrieveView(props) {
    return (
        <GenericView>
            <Card body>
                I am a full-fledge view provided by the default example App.
                The ID of the object I am displaying is: {props.id}
            </Card>
        </GenericView>
    );
}

export default RetrieveView;
