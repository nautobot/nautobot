/**
 * A Markdownlint Plugin that checks whether the relative link urls are file-relative instead of
 * directory-relative to ensure that mkdocs validates the links.
 */

// All external urls should have a scheme, i.e. http://, https:// or mailto:
const externalUrl = /^[a-z0-9+.-]+:/;
// linking within the same file is just (#<anchor-name>)
const anchor = /^#/;
const markdownFile = /.md/;

module.exports = {
    names: ['NAUTOBOTMD001', 'nautobotmd.filerelativelinks'],
    description: 'All relative links should be file-relative',
    tags: ['links'],
    function: function rule(params, onError) {
        params.tokens
            .filter(function filterToken(token) {
                return token.type === 'inline';
            })
            .forEach(function forToken(inline) {
                inline.children
                    .filter(function filterChild(child) {
                        return child.type === 'link_open';
                    })
                    .forEach(function forToken(link) {
                        if (link.attrs[0] && link.attrs[0][0] === 'href') {
                            const href = link.attrs[0][1];

                            let isMarkdownFile = markdownFile.test(href.toLowerCase());
                            let isExternalUrl = externalUrl.test(href.toLowerCase());
                            let isAnchor = anchor.test(href.toLowerCase());
                            if (isExternalUrl || isAnchor) {
                                // pass
                            }
                            else if ( !isMarkdownFile ) {
                                let range = null;
                                const column = link.line.indexOf(href);
                                const length = href.length;
                                range = [column, length];
                                onError({
                                    lineNumber: link.lineNumber,
                                    detail: 'Link ' + href,
                                    range
                                });
                            }
                        }
                    });
            });
    }
};