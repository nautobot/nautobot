const { CracoAliasPlugin } = require("react-app-alias-ex");

// Suppress console logging unless debugging is explicitly enabled.
if (!process.env.NAUTOBOT_DEBUG) {
    console.log = function () {};
}

module.exports = {
    plugins: [
        {
            plugin: CracoAliasPlugin,
        },
    ],

    webpack: {
        configure: (webpackConfig) => {
            // TODO(jathan): Still working out quirks on how to properly tie together static files and self-hosting
            // config.output.path = path.resolve(__dirname, "build/static")  // Should be in STATICFILES_DIRS
            // config.output.publicPath = process.env.NAUTOBOT_STATIC_URL // Should match STATIC_URL
            webpackConfig.output.filename = "static/js/[name].js"; // No filename hashing; Django collectstatic takes care of this
            webpackConfig.output.assetModuleFilename =
                "static/media/[name].[ext]";
            webpackConfig.output.chunkFilename =
                "static/js/[id]-[chunkhash].js"; // DO have Webpack hash chunk filename

            // TODO: tradeoffs here for performance, see https://webpack.js.org/configuration/devtool/
            webpackConfig.devtool = "eval-cheap-module-source-map";

            // Plugin item 5 is the `MiniCssExtractPlugin`. Overload it to not hash the CSS filename.
            webpackConfig.plugins[5].options.filename = "static/css/[name].css";

            // TODO(jathan): This might be safely deleted.
            webpackConfig.devServer = {
                writeToDisk: true, // Write files to disk in dev mode so Django can serve the assets
            };
            return webpackConfig;
        },
    },
};
