/**
 * This is a wrapper around react-app-alias and react-app-alias-ex that addresses
 * a bug in react-app-alias-ex where it does not properly resolve the path to
 * node_modules when running Jest tests.
 *
 * See: https://github.com/oklas/react-app-alias/issues/95
 */
const path = require("path");
const paths = require("react-scripts/config/paths");
const { aliasJest: aliasJestSafe, defaultOptions } = require("react-app-alias");
const { aliasWebpack } = require("react-app-alias-ex");

function aliasJest(options) {
    const aliasMap = defaultOptions(options).aliasMap;
    const aliasJestInstance = aliasJestSafe(aliasMap);
    return function (config) {
        const expanded = aliasJestInstance(config);
        const returning = {
            ...expanded,
            moduleDirectories: [
                ...(config.moduleDirectories || ["node_modules"]), // react-app-alias-ex defaulted to [] instead of the Jest default of ["node_modules"]
                path.resolve(paths.appPath, "node_modules"),
            ],
        };
        return returning;
    };
}

const NautobotCracoAliasPlugin = {
    overrideWebpackConfig: function ({ webpackConfig, pluginOptions }) {
        return aliasWebpack(pluginOptions)(webpackConfig);
    },
    overrideJestConfig: function ({ jestConfig, pluginOptions }) {
        return aliasJest(pluginOptions)(jestConfig);
    },
};

module.exports = {
    NautobotCracoAliasPlugin,
};
