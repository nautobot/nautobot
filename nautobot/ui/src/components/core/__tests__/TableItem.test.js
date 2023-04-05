import React from "react";
import { render } from "@testing-library/react";
import BSTableItem from "../TableItem";

describe("BSTableItem", () => {
    it("renders minus icon when obj is null", () => {
        render(<BSTableItem name="test" obj={null} />);
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
        const { container } = render(<BSTableItem name="test" obj={obj} />);
        expect(container.innerHTML).toBe(
            `<span class="badge" style="background-color: rgb(18, 52, 86);">${obj[0].label}</span>`
        );
    });

    it("renders text when obj is an object", () => {
        const obj = { display: "test" };
        const { container } = render(<BSTableItem name="test" obj={obj} />);
        expect(container.innerHTML).toBe(obj.display);
    });

    it("renders text when obj is a string", () => {
        const obj = "test";
        const { container } = render(<BSTableItem name="test" obj={obj} />);
        expect(container.innerHTML).toBe(obj);
    });

    it("renders minus icon when obj is an empty string", () => {
        render(<BSTableItem name="test" obj="" />);
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
