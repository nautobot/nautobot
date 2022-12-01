import { Outlet } from "react-router-dom";

export default function Plugins(){
    return (
        <div>
            <h1>Plugins Page</h1>
            <Outlet />
        </div>
    )
}