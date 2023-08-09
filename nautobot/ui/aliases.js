/**
 * This module provides utility functions to create Webpack and Jest alias configurations
 * from the `jsconfig.json` file and its extended configurations.
 * 
 * Summary:
 * 1. Reading the `jsconfig.json` and its extended configurations and Merging the base and extended configurations.
 * 2. Parsing the `compilerOptions.paths` from the merged configuration to generate:
 *    - Webpack aliases: Used to simplify import paths in Webpack configurations.
 *    - Jest aliases: Used to map module paths for Jest tests.
**/

const path = require("path");
const fs = require("fs");
const jsconfig = require("./jsconfig.json");

const appDirectory = fs.realpathSync(process.cwd());
const resolveApp = (relativePath) => path.resolve(appDirectory, relativePath);

const jsconfigPaths = resolveApp(jsconfig.extends);
const extendedJsConfig = require(jsconfigPaths);
const compiledJsconfig = { ...jsconfig, ...extendedJsConfig };

const createWebpackAliasesFromJsconfig = (jsconfig) => {
    const webpackAliases = {};

    for (let key in jsconfig.compilerOptions.paths) {
        // Remove the /* from the key
        const aliasKey = key.replace("/*", "");
        // Remove the /* from the value and resolve the path
        const aliasValue = jsconfig.compilerOptions.paths[key][0].replace(
            "/*",
            ""
        );
        webpackAliases[aliasKey] = resolveApp(aliasValue);
    }
    return webpackAliases;
};

const createJestAliasesFromJsconfig = (jsconfig) => {
    const jestAliases = {};

    for (let key in jsconfig.compilerOptions.paths) {
        // Remove the /* from the key
        const aliasKey = key.replace("/*", "");
        // Remove the /* from the value and resolve the path
        const aliasValue = jsconfig.compilerOptions.paths[key][0].replace(
            "/*",
            ""
        );
        jestAliases[`^${aliasKey}/(.*)$`] = `${resolveApp(aliasValue)}/$1`;
    }
    return jestAliases;
};

module.exports = {
    webpack: createWebpackAliasesFromJsconfig(compiledJsconfig),
    jest: createJestAliasesFromJsconfig(compiledJsconfig),
};
