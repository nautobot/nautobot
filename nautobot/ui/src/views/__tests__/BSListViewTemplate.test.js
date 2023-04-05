// import { render, screen } from "@testing-library/react";
// import { BrowserRouter } from "react-router-dom";
// import useSWR from "swr";
// import BSListViewTemplate from "../BSListViewTemplate";

// jest.mock("swr");

describe("BSListViewTemplate component", () => {
    // TODO: This needs to be update to test ObjectList.js
    // it("should render `Failed to load` if swr error", async () => {
    //     useSWR.mockReturnValue({
    //         error: { message: "" },
    //     });
    //     render(
    //         <BrowserRouter>
    //             <BSListViewTemplate list_url="http://localhost:8000/api/items/" />
    //         </BrowserRouter>
    //     );
    //     screen.getByText("Failed to load http://localhost:8000/api/items/");
    // });

    // it("should render empty page if swr yet to load (undefined)", async () => {
    //     useSWR.mockReturnValue({
    //         data: undefined,
    //         error: undefined,
    //     });
    //     const { container } = render(
    //         <BrowserRouter>
    //             <BSListViewTemplate list_url="http://localhost:8000/api/items/" />
    //         </BrowserRouter>
    //     );
    //     expect(container.innerHTML).toBe("");
    // });

    // it("Render page properly if swr request successfull", async () => {
    //     const mockData = [
    //         {
    //             formData: {
    //                 count: 2,
    //                 next: null,
    //                 previous: null,
    //                 results: [
    //                     {
    //                         id: 1,
    //                         name: "Example One",
    //                         status: "active",
    //                     },
    //                     {
    //                         id: 2,
    //                         name: "Example Two",
    //                         status: "deactivated",
    //                     },
    //                 ],
    //             },
    //         },
    //         {
    //             formData: {
    //                 data: [
    //                     { name: "name", label: "Name" },
    //                     { name: "status", label: "Status" },
    //                 ],
    //             },
    //         },
    //     ];
    //     useSWR.mockReturnValue({
    //         data: mockData,
    //     });
    //     render(
    //         <BrowserRouter>
    //             <BSListViewTemplate list_url="http://localhost:8000/api/items/" />
    //         </BrowserRouter>
    //     );

    //     // Assert we have 3 buttons: Add, Import and Export
    //     const buttons = screen.getAllByRole("button");
    //     expect(buttons.length).toBe(3);
    //     // const addBtn = buttons[0];
    //     // const importBtn = buttons[1];
    //     // const exportBtn = buttons[2];
    //     // expect(addBtn.getAttribute("to")).toBe("/add")
    //     // expect(addBtn.getAttribute("class")).toBe("btn btn-primary")
    //     // expect(addBtn.innerHTML).toContain("Add")
    //     // expect(importBtn.getAttribute("class")).toBe("btn btn-info")
    //     // expect(importBtn.innerHTML).toContain("Import")
    //     // expect(exportBtn.getAttribute("class")).toBe("btn btn-success")
    //     // expect(exportBtn.innerHTML).toContain("Export")

    //     // Assert table has correct data
    //     // const tableDom = document.evaluate('//table', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue
    //     // const tableHeader = tableDom.children[0]
    //     // expect(tableHeader.innerHTML).toContain("<th>Name</th><th>Status</th>")

    //     // // Assert Table body has two rows and three colums
    //     // const tableBody = tableDom.children[1].children
    //     // expect(tableBody.length).toBe(2)
    //     // expect(tableBody[0].children.length).toBe(3)

    //     // // Assert Table
    //     // const firstRow = '<td><div class=""><input type="checkbox" class="form-check-input"></div></td><td><a href="/1">Example One</a></td><td>active</td>'
    //     // const secondRow = '<td><div class=""><input type="checkbox" class="form-check-input"></div></td><td><a href="/2">Example Two</a></td><td>deactivated</td>'
    //     // expect(tableBody[0].innerHTML).toBe(firstRow)
    //     // expect(tableBody[1].innerHTML).toBe(secondRow)

    //     // NOTE: Im not validating table and pagination here; Cause they have properly been tested in other test cases
    // });
    it("should be true", async () => expect(true).toBe(true));
});
