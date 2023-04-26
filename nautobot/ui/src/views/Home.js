import { Alert } from "@chakra-ui/react"; // TODO: import from nautobot-ui when available
import GenericView from "@views/generic/GenericView";

export default function Home() {
    return (
        <GenericView>
            <Alert status="success">
                Hello from React! 👋 <br />
            </Alert>
        </GenericView>
    );
}
