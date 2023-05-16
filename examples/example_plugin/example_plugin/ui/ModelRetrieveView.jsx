import { useParams } from "react-router-dom";


export default function ModelRetrieveView(props){
    const { pk } = useParams();
    return (
            <div>Im a App provided route view with pk: { pk }.</div>
    )
}