import "@testing-library/jest-dom";
import React from "react";
import { render, screen } from "@testing-library/react";
import { ObjectTableItem } from "../ObjectTable";

describe("TableItem", () => {
    it("renders em dash when obj is null", () => {
        const { container } = render(
            <ObjectTableItem name="test" obj={null} />
        );
        expect(container.innerHTML).toBe("—");
    });

    it("renders span with className=badge when obj is an array", () => {
        const obj = [{ label: "test", color: "123456" }];
        render(<ObjectTableItem name="test" obj={obj} />);
        expect(screen.getByRole("button")).toHaveStyle(
            `background-color: #${obj[0].color}`
        );
        expect(screen.getByRole("button").innerHTML).toBe(obj[0].label);
    });

    it("renders text when obj is an object", () => {
        const obj = { display: "test" };
        const { container } = render(<ObjectTableItem name="test" obj={obj} />);
        expect(container.innerHTML).toBe(obj.display);
    });

    it("renders text when obj is a string", () => {
        const obj = "test";
        const { container } = render(<ObjectTableItem name="test" obj={obj} />);
        expect(container.innerHTML).toBe(obj);
    });

    it("renders em dash when obj is an empty string", () => {
        const { container } = render(<ObjectTableItem name="test" obj="" />);
        expect(container.innerHTML).toBe("—");
    });
});
