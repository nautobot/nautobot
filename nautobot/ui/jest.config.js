const modules = require("./config/modules");

module.exports = {
    roots: ["<rootDir>/src"],
    collectCoverageFrom: ["src/**/*.{js,jsx}", "!src/**/*.d.ts"],
    setupFiles: ["react-app-polyfill/jsdom"],
    setupFilesAfterEnv: [],
    testMatch: [
        "<rootDir>/src/**/__tests__/**/*.{js,jsx}",
        "<rootDir>/src/**/*.{spec,test}.{js,jsx}",
    ],
    testEnvironment: "jsdom",
    transform: {
        "^.+\\.(js|jsx|mjs|cjs)$": "<rootDir>/config/jest/babelTransform.js",
        "^.+\\.css$": "<rootDir>/config/jest/cssTransform.js",
        "^(?!.*\\.(js|jsx|mjs|cjs|css|json)$)":
            "<rootDir>/config/jest/fileTransform.js",
    },
    transformIgnorePatterns: [
        "[/\\\\]node_modules[/\\\\].+\\.(js|jsx|mjs|cjs)$",
        "^.+\\.module\\.(css|sass|scss)$",
    ],
    modulePaths: [],
    moduleNameMapper: {
        "^react-native$": "react-native-web",
        "^.+\\.module\\.(css|sass|scss)$": "identity-obj-proxy",
        ...modules.jestAliases,
    },
    moduleFileExtensions: ["web.js", "js", "json", "web.jsx", "jsx", "node"],
    watchPlugins: [
        "jest-watch-typeahead/filename",
        "jest-watch-typeahead/testname",
    ],
    resetMocks: true,
};
