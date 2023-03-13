const {aliasDangerous, configPaths} = require('react-app-rewire-alias/lib/aliasDangerous')
const path = require("path")

// Suppress console logging unless debugging is explicitly enabled.
if (!process.env.NAUTOBOT_DEBUG) {
  console.log = function () {}
}

/*
console.log()
console.log(">>> `nautobot-server build` settings:")
console.log("STATIC_URL      = " + process.env.NAUTOBOT_STATIC_URL)
console.log("STATICFILES_DIR = " + process.env.NAUTOBOT_STATICFILES_DIR)
console.log("__dirname       = " + __dirname)
*/

module.exports = function override(config) {
  aliasDangerous({
      ...configPaths('jsconfig.json')
  })(config)

  /*
  console.log(">> BEFORE config.output:")
  console.log(config.output)
  console.log()
  */

  // TODO(jathan): Still working out quirks on how to properly tie together static files and self-hosting
  // config.output.path = path.resolve(__dirname, "build/static")  // Should be in STATICFILES_DIRS
  // config.output.publicPath = process.env.NAUTOBOT_STATIC_URL // Should match STATIC_URL
  config.output.filename =  "static/js/[name].js" // No filename hashing; Django collectstatic takes care of this
  config.output.assetModuleFilename = "static/media/[name].[ext]"
  config.output.chunkFilename = "static/js/[id]-[chunkhash].js" // DO have Webpack hash chunk filename

  // TODO: tradeoffs here for performance, see https://webpack.js.org/configuration/devtool/
  config.devtool = 'eval-cheap-module-source-map'
  /*
  console.log(">> AFTER config.output:")
  console.log(config.output)
  console.log()
  */

  // Plugin item 5 is the `MiniCssExtractPlugin`. Overload it to not hash the CSS filename.
  config.plugins[5].options.filename = "static/css/[name].css"

  // TODO(jathan): This might be safely deleted.
  config.devServer = {
    writeToDisk: true, // Write files to disk in dev mode so Django can serve the assets
  }

  return config
}
