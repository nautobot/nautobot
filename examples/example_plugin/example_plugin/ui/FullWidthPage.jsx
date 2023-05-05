import { Card } from '@chakra-ui/react';  // TODO: import from nautobot-ui when available.

export function MyFancyCard(props) {
    return <Card body>I am a full-fledge component provided by the default example App. The ID of the object I am displaying is: {props.id}</Card>;
}

export default MyFancyCard;
