'use strict'

import path from 'node:path';
import autoprefixer from 'autoprefixer';
import miniCssExtractPlugin from 'mini-css-extract-plugin'
/* TODO: bootstrap 5 usage doesn't coexist well with stylelint defaults */
// import stylelintPlugin from 'stylelint-webpack-plugin';

const __dirname = import.meta.dirname;

export default [
    {
        mode: 'production',
        devtool: 'source-map',
        entry: {
            nautobot: path.resolve('src', 'js', 'nautobot.js'),
        },
        output: {
            filename: 'js/[name].js',
            path: path.resolve(__dirname, 'dist')
        },
        optimization: {
            splitChunks: {
                chunks: 'all',
                name: 'libraries'
            }
        },
        plugins: [
            // TODO: add CSS/SCSS linting to the build
            // new stylelintPlugin(
            //     {
            //         files: path.join('src', '**/*.s?(a|c)ss'),
            //     }
            // ),
            new miniCssExtractPlugin(
                {
                    filename: 'css/[name].css'
                }
            )
        ],
        module: {
            rules: [
                // TODO: add JS linting with eslint to the build
                // {
                //     test: /\.js$/,
                //     include: path.resolve(__dirname, 'src', 'js'),
                //     enforce: 'pre',
                //     loader: 'eslint-loader',
                //     options: {
                //         emitWarning: true,
                //     }
                // },
                {
                    test: /\.(s?css)$/,
                    use: [
                        {
                            loader: miniCssExtractPlugin.loader
                        },
                        {
                            loader: 'css-loader'
                        },
                        {
                            loader: 'postcss-loader',
                            options: {
                                postcssOptions: {
                                    plugins: [
                                        autoprefixer
                                    ]
                                }
                            }
                        },
                        {
                            loader: 'sass-loader',
                            options: {
                                sassOptions: {
                                    quietDeps: true,
                                    silenceDeprecations: ['import']
                                }
                            }
                        }
                    ]
                }
            ]
        }
    },
    {
        mode: 'production',
        devtool: 'source-map',
        entry: {
            "nautobot-graphiql": path.resolve('src', 'js', 'nautobot-graphiql.js')
        },
        output: {
            filename: 'js/[name].js',
            path: path.resolve(__dirname, 'dist')
        },
        optimization: {
            splitChunks: {
                chunks: 'all',
                name: 'graphql-libraries'
            }
        },
        plugins: [
            new miniCssExtractPlugin(
                {
                    filename: 'css/[name].css'
                }
            )
        ],
        module: {
            rules: [
                {
                    test: /\.(css)$/,
                    use: [
                        {
                            loader: miniCssExtractPlugin.loader
                        },
                        {
                            loader: 'css-loader'
                        }
                    ]
                }
            ]
        }
    },
    {
        mode: 'production',
        devtool: 'source-map',
        entry: {
            materialdesignicons: '@mdi/font/css/materialdesignicons.css',
        },
        output: {
            filename: 'js/[name].js',
            path: path.resolve(__dirname, 'dist')
        },
        plugins: [
            new miniCssExtractPlugin(
                {
                    filename: 'css/[name].css',
                    chunkFilename: 'css/[id].css',
                }
            )
        ],
        module: {
            rules: [
                {
                    test: /\.(css|scss)$/,
                    use: [
                        {
                            loader: miniCssExtractPlugin.loader
                        },
                        {
                            loader: 'css-loader'
                        },
                        {
                            loader: 'sass-loader'
                        }
                    ]
                },
                {
                    test: /\.(woff(2)?|ttf|eot|svg)(\?v=\d+\.\d+\.\d+)?$/,
                    type: 'asset/resource'
                }
            ]
        }
    }
]
