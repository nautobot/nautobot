const babelJest = require("babel-jest").default;

module.exports = babelJest.createTransformer({
    presets: [
        [
            require.resolve("babel-preset-react-app"),
            {
                runtime: "automatic",
            },
        ],
    ],
    babelrc: false,
    configFile: false,
});
