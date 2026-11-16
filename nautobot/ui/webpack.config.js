'use strict'

import path from 'node:path';
import autoprefixer from 'autoprefixer';
import CopyPlugin from 'copy-webpack-plugin';
import webpack from 'webpack';

const __dirname = import.meta.dirname;

export default [
    {
        mode: 'production',
        devtool: 'source-map',
        entry: {
            nautobot: [path.resolve('src', 'scss', 'nautobot.scss'), path.resolve('src', 'js', 'nautobot.js')],
        },
        output: {
            filename: 'js/[name].js',
            cssFilename: 'css/[name].css',
            path: path.resolve(__dirname, '..', 'project-static', 'dist')
        },
        optimization: {
            splitChunks: {
                chunks: 'all',
                minSize: 0,
                maxSize: 100000000,
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
            })
        ],
        module: {
            rules: [
                {
                    test: /\.(scss)$/,
                    type: "css/auto",
                    use: [
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
        experiments: {
            css: true,
        },
        output: {
            filename: 'js/[name].js',
            cssFilename: 'css/[name].css',
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
    },
    {
        mode: 'production',
        devtool: 'source-map',
        entry: {
            materialdesignicons: '@mdi/font/css/materialdesignicons.css',
        },
        experiments: {
            css: true,
        },
        output: {
            filename: 'js/[name].js',
            cssFilename: 'css/[name].css',
            cssChunkFilename: 'css/[name].[id].css',
            path: path.resolve(__dirname, '..', 'project-static', 'dist')
        },
        module: {
            rules: [
                {
                    test: /\.(css|scss)$/,
                    type: "css/auto",
                    use: [
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
