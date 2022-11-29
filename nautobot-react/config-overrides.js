/* config-overrides.js */

const HtmlWebPackPlugin = require('html-webpack-plugin');
const ModuleFederationPlugin = require('webpack/lib/container/ModuleFederationPlugin');

module.exports = function override(config, env) {
  //do stuff with the webpack config...
  console.log("\n\n>>> I HAVE OVERRIDEN THE WEBPACK CONFIG! <<< \n\n");
	// console.log("\n\nExisting plugins: " + config.plugins + "\n\n");

	plugins = [
		new ModuleFederationPlugin({
			name: 'nautobot',
			library: { type: 'var', name: 'nautobot' },
			filename: 'remoteEntry.js',
			exposes: {
				NautobotCheck: './src/common/shared/NautobotCheck',
				NautobotInput: './src/common/shared/NautobotInput',
				NautobotSelect: './src/common/shared/NautobotSelect',
				NautobotTable: './src/common/shared/NautobotTable',
				ListViewTemplate: './src/common/template/ListViewTemplate',
				ObjectRetrieveTemplate: './src/common/template/ObjectRetrieveTemplate',
			},
			shared: ['react', 'react-bootstrap', 'react-dom', 'react-router-dom']
		}),
		// No idea if this is actually needed. Just duplicating it from other config examples.
		new HtmlWebPackPlugin({
			template: './public/index.html'
		})
	]

	// Extend existing plugins array with ours.
	config.plugins.push(...plugins)

  return config;
}
