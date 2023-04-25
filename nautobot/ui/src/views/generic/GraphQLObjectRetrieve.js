import { useQuery, gql } from "@apollo/client";
import { useParams } from "react-router-dom";


const GET_LOCATION = gql`
  query GetLocation($id: String!) {
    locations(id: [$id]) {
      id, name, description
    } }
`;


export default function ObjectRetrieve() {
    const { app_name, model_name, object_id } = useParams();
    const { loading, error, data } = useQuery(GET_LOCATION, { variables: { id: object_id } });

    if (loading) return <p>Loading...</p>;
    if (error) return <p>Error : {error.message}</p>;

    return data.locations.map(({ id, name, description }) => (
        <div>
            <h2>{name}</h2>
            <h3>({id})</h3>
            <br />
            <b>About this location:</b>
            <p>{description}</p>
            <br />
        </div>
    ))
}
