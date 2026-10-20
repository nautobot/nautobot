'use strict'

import fs from 'node:fs';
import path from 'node:path';
import autoprefixer from 'autoprefixer';
import CopyPlugin from 'copy-webpack-plugin';
import miniCssExtractPlugin from 'mini-css-extract-plugin'

const __dirname = import.meta.dirname;

// Redoc hardcodes its sidebar logo as an <img> loaded from Redocly's CDN; inline a vendored copy instead so that
// the API docs make no external requests.
const REDOC_LOGO_CDN_URL = 'https://cdn.redoc.ly/redoc/logo-mini.svg';
const inlineRedocLogo = (content) => {
    const source = content.toString();
    if (!source.includes(REDOC_LOGO_CDN_URL)) {
        throw new Error(`${REDOC_LOGO_CDN_URL} not found in redoc.standalone.js; has Redoc changed how it loads its logo?`);
    }
    const logo = fs.readFileSync(path.resolve(__dirname, 'src', 'img', 'redoc-logo-mini.svg')).toString('base64');
    return source.replaceAll(REDOC_LOGO_CDN_URL, `data:image/svg+xml;base64,${logo}`);
};

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
                    // Swagger UI and Redoc are shipped as pre-built, pre-minified bundles, so we copy them as-is rather
                    // than re-bundling, and mark them as `minimized` so that Terser doesn't re-minify them either.
                    ...[
                        'LICENSE',
                        'swagger-ui.css',
                        'swagger-ui.css.map',
                        'swagger-ui-bundle.js',
                        'swagger-ui-bundle.js.LICENSE.txt',
                        'swagger-ui-bundle.js.map',
                        'swagger-ui-standalone-preset.js',
                        'swagger-ui-standalone-preset.js.LICENSE.txt',
                        'swagger-ui-standalone-preset.js.map',
                    ].map((filename) => ({
                        from: path.resolve(__dirname, 'node_modules', 'swagger-ui-dist', filename),
                        to: path.resolve(__dirname, '..', 'project-static', 'dist', 'swagger-ui'),
                        info: { minimized: true },
                    })),
                    ...[
                        'LICENSE',
                        'bundles/redoc.standalone.js.LICENSE.txt',
                        'bundles/redoc.standalone.js.map',
                    ].map((filename) => ({
                        from: path.resolve(__dirname, 'node_modules', 'redoc', filename),
                        to: path.resolve(__dirname, '..', 'project-static', 'dist', 'redoc'),
                        info: { minimized: true },
                    })),
                    {
                        from: path.resolve(__dirname, 'node_modules', 'redoc', 'bundles', 'redoc.standalone.js'),
                        to: path.resolve(__dirname, '..', 'project-static', 'dist', 'redoc'),
                        transform: inlineRedocLogo,
                        info: { minimized: true },
                    },
                ],
            }),
            new miniCssExtractPlugin(
                {
                    filename: 'css/[name].css'
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
        entry: {
            "nautobot-graphiql": path.resolve('src', 'js', 'nautobot-graphiql.js')
        },
        output: {
            filename: 'js/[name].js',
            path: path.resolve(__dirname, '..', 'project-static', 'dist')
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
