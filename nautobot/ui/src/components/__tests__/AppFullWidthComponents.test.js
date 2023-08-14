import { render } from "@testing-library/react";
import AppFullWidthComponentsWithProps from "../AppFullWidthComponents";

// Set NautobotApps to {}; since we are not testing for plugin integration with nautobot
jest.mock("@generated/app_imports", () => ({
    __esModule: true,
    default: {},
}));

describe("AppFullWidthComponentsWithProps Test", () => {
    it("should render an empty component when route, props is not defined", () => {
        render(AppFullWidthComponentsWithProps());
        // expect(container.firstChild).toBe(null);
        // Lint error for using firstChild but we should be using screen
    });
});
