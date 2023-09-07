import { Box } from '@nautobot/nautobot-ui';

export function MyFancyCard(props) {
    return <Box body>I am a full-fledged component provided by the default example App. The ID of the object I am displaying is: {props.id}</Box>;
}

export default MyFancyCard;
