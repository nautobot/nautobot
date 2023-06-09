import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import NautobotTable from "../ObjectTable";

const mockHeaders = [
    { key: "name", dataIndex: "name", title: "Name" },
    { key: "description", dataIndex: "description", title: "Description" },
];
const mockData = [
    { id: 1, name: "Item 1", description: "Description 1" },
    { id: 2, name: "Item 2", description: "Description 2" },
];

describe("NautobotTable", () => {
    it("renders table headers and data", () => {
        render(
            <BrowserRouter>
                <NautobotTable
                    defaultHeaders={mockHeaders}
                    tableHeaders={mockHeaders}
                    tableData={mockData}
                />
            </BrowserRouter>
        );

        // Check that table headers are rendered
        screen.getByText("Name");
        screen.getByText("Description");

        // // Check that table data is rendered
        screen.getByText("Item 1");
        screen.getByText("Description 1");
        screen.getByText("Item 2");
        screen.getByText("Description 2");

        // Check that a checkbox is rendered for each item
        const checkboxes = screen.getAllByRole("checkbox");
        expect(checkboxes.length).toBe(3);
    });
});
