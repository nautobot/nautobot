import { render, screen, act, fireEvent } from "@testing-library/react"
import BSNavBar from "../BSNavBar"
import useSWR from "swr";
import { BrowserRouter } from "react-router-dom";

jest.mock("swr")


describe("BSNavBar Test", () => {
    it("should render `Failed to load menu` if api error", () => {
        const errorMessage = "Failed to load menu";
        useSWR.mockReturnValue({
            error: { message: errorMessage },
        });
        const { container } = render(<BSNavBar />);
        expect(container.innerHTML).toBe("<div>Failed to load menu</div>")
    })

    it("should render an empty html tag if api is yet to return value", () => {
        useSWR.mockReturnValue({
            data: undefined,
        });
        const { container } = render(<BSNavBar />);
        expect(container.innerHTML).toBe("")
    })

    it("should render nav correctly, if api request successfull", async () => {
        const menuData = [
            {
                name: "Menu 1",
                properties: { groups: {} }
            },
            {
                name: "Menu 2",
                properties: { groups: {} }
            },
            {
                name: "Menu 3",
                properties: { groups: {} }
            },
        ]
        useSWR.mockReturnValue({
            data: menuData,
        });
        // Using BrowserRouter here because BSNavBar can only be utilized withing a Router
        const { container } = render(<BrowserRouter><BSNavBar /></BrowserRouter>);
        container.querySelector("nav")
        await screen.findByText('Menu 1')
        await screen.findByText('Menu 2')
        await screen.findByText('Menu 3')
    })

    it("should render nav correctly with children when dropdown clicked", async () => {
        const menuData = [
            {
                name: "Menu 1",
                properties: {
                    groups: {
                        "Group 1": {
                            items: {
                                "/path1": { name: "Menu Item 1" },
                                "/path2": { name: "Menu Item 2" },
                            },
                        },
                    },
                },
            },
        ]
        useSWR.mockReturnValue({
            data: menuData,
        });
        render(<BrowserRouter><BSNavBar /></BrowserRouter>);
        const dropdownMenu = await screen.findByRole('button', { name: 'Menu 1' })
        fireEvent.click(dropdownMenu)

        await screen.findByText("Menu Item 1")
    })
})