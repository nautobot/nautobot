'use strict'

import path from 'node:path';
import autoprefixer from 'autoprefixer';
import CopyPlugin from 'copy-webpack-plugin';
import miniCssExtractPlugin from 'mini-css-extract-plugin'
import MinimizerPlugin from 'minimizer-webpack-plugin';
import webpack from 'webpack';

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
            path: path.resolve(__dirname, '..', 'project-static', 'dist')
        },
        optimization: {
            splitChunks: {
                chunks: 'all',
                name: 'libraries'
            }
        },
        plugins: [
            new CopyPlugin({
                patterns: [
                    {
                        from: path.resolve(__dirname, 'node_modules', 'highlight.js', 'styles', 'github.min.css'),
                        to: path.resolve(__dirname, '..', 'project-static', 'dist', 'css'),
                    },
                    {
                        from: path.resolve(__dirname, 'node_modules', 'highlight.js', 'styles', 'github-dark.min.css'),
                        to: path.resolve(__dirname, '..', 'project-static', 'dist', 'css'),
                    },
                ],
            }),
            new miniCssExtractPlugin(
                {
                    filename: 'css/[name].css'
                }
            ),
            new webpack.optimize.LimitChunkCountPlugin(
                {
                    maxChunks: 2,
                }
            )
        ],
        module: {
            rules: [
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
        target: 'universal',
        entry: {
            "nautobot-graphiql": path.resolve('src', 'js', 'nautobot-graphiql.js')
        },
        output: {
            filename: 'js/[name].js',
            path: path.resolve(__dirname, '..', 'project-static', 'dist')
        },
        optimization: {
            runtimeChunk: 'single',
            splitChunks: {
                chunks: 'all',
                minSize: 0,
                maxSize: 100000000,
                cacheGroups: {
                    vendor: {
                        test: /[\\/]node_modules[\\/]/,
                        name(module) {
                            const packageName = module.identifier().match(/[\\/]node_modules[\\/](.*?)([\\/]|$)/)[1];
                            return `npm/${packageName.replace('@', '')}`;
                        }
                    }
                }
            }
        },
        plugins: [
            new miniCssExtractPlugin(
                {
                    filename: 'css/[name].css'
                }
            ),
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
            path: path.resolve(__dirname, '..', 'project-static', 'dist')
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
