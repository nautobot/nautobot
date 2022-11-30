const {aliasDangerous, configPaths} = require('react-app-rewire-alias/lib/aliasDangerous')

module.exports = function override(config) {
    aliasDangerous({
        ...configPaths('jsconfig.json')
    })(config)

    return config
}