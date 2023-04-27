import "@testing-library/jest-dom";
import React from "react";
import { render, screen } from "@testing-library/react";
import TableItem from "../TableItem";

describe("TableItem", () => {
    it("renders minus icon when obj is null", () => {
        render(<TableItem name="test" obj={null} />);
        const minusIcon = document.evaluate(
            "//svg",
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        expect(minusIcon.singleNodeValue.getAttribute("class")).toBe(
            "svg-inline--fa fa-minus "
        );
    });

    it("renders span with className=badge when obj is an array", () => {
        const obj = [{ label: "test", color: "123456" }];
        render(<TableItem name="test" obj={obj} />);
        expect(screen.getByRole("button")).toHaveStyle(
            `background-color: #${obj[0].color}`
        );
        expect(screen.getByRole("button").innerHTML).toBe(obj[0].label);
    });

    it("renders text when obj is an object", () => {
        const obj = { display: "test" };
        const { container } = render(<TableItem name="test" obj={obj} />);
        expect(container.innerHTML).toBe(obj.display);
    });

    it("renders text when obj is a string", () => {
        const obj = "test";
        const { container } = render(<TableItem name="test" obj={obj} />);
        expect(container.innerHTML).toBe(obj);
    });

    it("renders minus icon when obj is an empty string", () => {
        render(<TableItem name="test" obj="" />);
        const minusIcon = document.evaluate(
            "//svg",
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        expect(minusIcon.singleNodeValue.getAttribute("class")).toBe(
            "svg-inline--fa fa-minus "
        );
    });
});
