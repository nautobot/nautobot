const path = require('path');
const fs = require('fs');
const jsconfig = require('./jsconfig.json');

const appDirectory = fs.realpathSync(process.cwd());
const resolveApp = relativePath => path.resolve(appDirectory, relativePath);

const jsconfigPaths = resolveApp(jsconfig.extends);
const extendedJsConfig = require(jsconfigPaths)
const compiledJsconfig = {...jsconfig, ...extendedJsConfig}

const createWebpackAliasesFromJsconfig = (jsconfig)  => {
  const webpackAliases = {};

  for (let key in jsconfig.compilerOptions.paths) {
    // Remove the /* from the key
    const aliasKey = key.replace('/*', '');
    // Remove the /* from the value and resolve the path
    const aliasValue = jsconfig.compilerOptions.paths[key][0].replace('/*', '');
    webpackAliases[aliasKey] = resolveApp(aliasValue);
  }
  return webpackAliases;
}

const createJestAliasesFromJsconfig = (jsconfig)  => {
  const webpackAliases = {};
  // ^@generated/(.*)$

  for (let key in jsconfig.compilerOptions.paths) {
    // Remove the /* from the key
    const aliasKey = key.replace('/*', '');
    // Remove the /* from the value and resolve the path
    const aliasValue = jsconfig.compilerOptions.paths[key][0].replace('/*', '');
    webpackAliases[`^${aliasKey}/(.*)$`] = `${resolveApp(aliasValue)}/$1`;
  }
  return webpackAliases;
}


module.exports = {
  "webpack": createWebpackAliasesFromJsconfig(compiledJsconfig),
  "jest": createJestAliasesFromJsconfig(compiledJsconfig),
}
