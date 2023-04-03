import { render, screen } from "@testing-library/react";
import AppFullWidthComponentsWithProps from "../AppFullWidthComponents";

// Set NautobotApps to {}; since we are not testing for plugin integration with nautobot
jest.mock("src/app_imports", () => ({
    __esModule: true,
    default: {},
}));

describe("AppFullWidthComponentsWithProps Test", () => {
    it("should render an empty component when route, props is not defined", () => {
        const { container } = render(AppFullWidthComponentsWithProps());
        expect(container.firstChild).toBe(null);
    });
});
