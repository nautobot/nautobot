import { __esModule } from "@testing-library/jest-dom/dist/matchers";
import Apps from "../Apps";

// As of now we are not testing any plugin integration; so mock default value would be empty
jest.mock("src/app_imports", () => ({
    __esModule: true,
    default: {},
}));

describe("get_components", () => {
    it("should return empty object with the expected keys if no plugins found", () => {
        expect(Apps.FullWidthComponents).toEqual({});
        expect(Apps.CustomViews).toEqual({});
    });
});
