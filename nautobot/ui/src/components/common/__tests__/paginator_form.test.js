import { render } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import PaginatorForm from "../paginator_form";

it("PaginatorForm", () => {
    render(
        <BrowserRouter>
            <PaginatorForm start={0} end={50} total_count={100} />
        </BrowserRouter>
    );
    // TODO(timizuo): Can test for more things
    // screen.findByText("Showing 0 - 50 of 100");
});
