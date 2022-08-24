/**
 * Plugin checks whether the relative link urls are file-relative instead of
 * directory-relative to ensure that mkdocs validates the links.
 */

 module.exports = {
	names: ['NAUTOBOTMD001', 'nautobotmd.filerelativelinks'],
	description: 'All relative links should be file-relative',
	tags: ['compliance'],
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
							const originalHref = link.attrs[0][1];
							const href = originalHref.toLowerCase();
							const testRelative = /^(?:\.\.?\/)/;
							const testMarkdownFile = /.md/;
							let isRelative = testRelative.test(href);
							let isMarkdownFile = testMarkdownFile.test(href);
							if (isRelative && !isMarkdownFile) {
								let range = null;
								const column = link.line.indexOf(originalHref);
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