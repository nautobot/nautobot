/* config-overrides.js */

const ModuleFederationPlugin = require('webpack/lib/container/ModuleFederationPlugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');


module.exports = function override(config, env) {
	const isEnvDevelopment = env === 'development';
	const isEnvProduction = env === 'production';

	//do stuff with the webpack config...
	console.log("\n\n>>> I HAVE OVERRIDEN THE WEBPACK CONFIG! <<< \n\n");
	// console.log("\n\nExisting plugins: " + config.plugins + "\n\n");

	plugins = [
		new ModuleFederationPlugin({
			name: 'nautobot',
			library: { type: 'var', name: 'nautobot' },
			filename: 'static/reactjs/nautobotRemoteEntry.js',
			exposes: {
				NautobotCheck: './src/common/shared/NautobotCheck',
				NautobotInput: './src/common/shared/NautobotInput',
				NautobotSelect: './src/common/shared/NautobotSelect',
				NautobotTable: './src/common/shared/NautobotTable',
				ListViewTemplate: './src/common/template/ListViewTemplate',
				ObjectRetrieveTemplate: './src/common/template/ObjectRetrieveTemplate',
			},

			// shared: [
			// 	{
			// 		'react': { 'singleton': true },
			// 		'react-dom': { 'singleton': true },
			// 	},
			// 	'react-bootstrap',
			// 	'react-router-dom'
			// ]
		}),

	]
	const miniCssOptions = {
		filename: 'static/reactcss/[name].[contenthash:8].css',
		chunkFilename: 'static/reactcss/[name].[contenthash:8].chunk.css',
	}
	if (isEnvProduction) {
		config.plugins.forEach((p, i) => {
			if (p instanceof MiniCssExtractPlugin) {
				config.plugins.splice(i, 1, new MiniCssExtractPlugin(miniCssOptions));
			}
		})
	}

	// Extend existing plugins array with ours.
	config.plugins.push(...plugins)

	config.output.filename = isEnvProduction ? 'static/reactjs/[name].[contenthash:8].js' : isEnvDevelopment && 'static/reactjs/bundle.js';
	config.output.chunkFilename = isEnvProduction ? 'static/reactjs/[name].[contenthash:8].chunk.js' : isEnvDevelopment && 'static/reactjs/[name].chunk.js';

	return config;
}
