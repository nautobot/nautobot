const fs = require("fs");
const path = require("path");
const paths = require("./paths");
const chalk = require("react-dev-utils/chalk");

/**
 * Get additional module paths based on the baseUrl of a compilerOptions object.
 *
 * @param {Object} options
 */
function getAdditionalModulePaths(options = {}) {
    const baseUrl = options.baseUrl;

    if (!baseUrl) {
        return "";
    }

    const baseUrlResolved = path.resolve(paths.appPath, baseUrl);

    // We don't need to do anything if `baseUrl` is set to `node_modules`. This is
    // the default behavior.
    if (path.relative(paths.appNodeModules, baseUrlResolved) === "") {
        return null;
    }

    // Allow the user set the `baseUrl` to `appSrc`.
    if (path.relative(paths.appSrc, baseUrlResolved) === "") {
        return [paths.appSrc];
    }

    // If the path is equal to the root directory we ignore it here.
    // We don't want to allow importing from the root directly as source files are
    // not transpiled outside of `src`. We do allow importing them with the
    // absolute path (e.g. `src/Components/Button.js`) but we set that up with
    // an alias.
    if (path.relative(paths.appPath, baseUrlResolved) === "") {
        return null;
    }

    // Otherwise, throw an error.
    throw new Error(
        chalk.red.bold(
            "Your project's `baseUrl` can only be set to `src` or `node_modules`." +
                " Create React App does not support other values at this time."
        )
    );
}

/**
 * Get webpack aliases based on the baseUrl of a compilerOptions object.
 *
 * Nautobot extends the base implementation provided by create-react-app to handle `options.paths` as well as `baseUrl`.
 *
 * @param {*} options
 */
function getWebpackAliases(options = {}) {
    const baseUrl = options.baseUrl;

    let aliases = {};

    if (!baseUrl) {
        return aliases;
    }

    const baseUrlResolved = path.resolve(paths.appPath, baseUrl);

    if (path.relative(paths.appPath, baseUrlResolved) === "") {
        aliases["src"] = paths.appSrc;
    }

    for (let key in options.paths) {
        // Remove the /* from the key
        const aliasKey = key.replace("/*", "");
        // Remove the /* from the value and resolve the path
        const aliasValue = options.paths[key][0].replace("/*", "");
        aliases[aliasKey] = path.resolve(paths.appPath, aliasValue);
    }

    return aliases;
}

/**
 * Get jest aliases based on the baseUrl of a compilerOptions object.
 *
 * Nautobot extends the base implementation provided by create-react-app to handle `options.paths` as well as `baseUrl`.
 *
 * @param {*} options
 */
function getJestAliases(options = {}) {
    const baseUrl = options.baseUrl;

    let aliases = {};

    if (!baseUrl) {
        return aliases;
    }

    const baseUrlResolved = path.resolve(paths.appPath, baseUrl);

    if (path.relative(paths.appPath, baseUrlResolved) === "") {
        aliases["^src/(.*)$"] = "<rootDir>/src/$1";
    }

    for (let key in options.paths) {
        // Remove the /* from the key
        const aliasKey = key.replace("/*", "");
        // Remove the /* from the value and resolve the path
        const aliasValue = options.paths[key][0].replace("/*", "");
        aliases[`^${aliasKey}/(.*)$`] = `${path.resolve(
            paths.appPath,
            aliasValue
        )}/$1`;
    }

    return aliases;
}

/**
 * Get modules and aliases provided based on our jsconfig.
 *
 * Nautobot simplified the base implementation provided by create-react-app by removing references to tsconfig.json.
 *
 */
function getModules() {
    const hasJsConfig = fs.existsSync(paths.appJsConfig);

    let config;

    if (hasJsConfig) {
        config = require(paths.appJsConfig);
        // handle 'extends' keyword in config
        const base_config = require(path.resolve(
            paths.appPath,
            config.extends
        ));
        config = { ...base_config, ...config };
    }

    config = config || {};
    const options = config.compilerOptions || {};

    const additionalModulePaths = getAdditionalModulePaths(options);

    return {
        additionalModulePaths: additionalModulePaths,
        webpackAliases: getWebpackAliases(options),
        jestAliases: getJestAliases(options),
    };
}

module.exports = getModules();
