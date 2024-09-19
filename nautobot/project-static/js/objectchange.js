require.config({ paths: { 'vs': '/static/monaco-editor-0.51.0/vs' }});
require(['vs/editor/editor.main'], function() {
    var diffRemoved = JSON.parse(document.getElementById('diff-removed-data').textContent);
    var diffAdded = JSON.parse(document.getElementById('diff-added-data').textContent);

    var originalModel = monaco.editor.createModel(JSON.stringify(diffRemoved, null, 2), 'json');
    var modifiedModel = monaco.editor.createModel(JSON.stringify(diffAdded, null, 2), 'json');

    // Determine if dark mode is active
    var isDarkMode = document.documentElement.dataset.theme === 'dark';

    var diffEditor = monaco.editor.createDiffEditor(document.getElementById('objectchange-diff-viewer'), {
        automaticLayout: true,
        contextmenu: false,
        enableSplitViewResizing: false,
        lineDecorationsWidth: 0,
        lineNumbers: 'off',
        matchBrackets: 'never',
        minimap: {enabled: false},
        overviewRulerBorder: false,
        overviewRulerLanes: 0,
        hideCursorInOverviewRuler: true,
        readOnly: true,
        renderIndentGuides: false,
        renderLineHighlight: 'none',
        renderSideBySide: true,
        renderWhitespace: 'none',
        renderOverviewRuler: false,
        scrollBeyondLastLine: false,
        scrollbar: {
            useShadows: false,
            vertical: 'hidden', 
        },
        theme: isDarkMode ? 'vs-dark' : 'vs-light',
        useInlineViewWhenSpaceIsLimited: false,
        wordWrap: 'off',
    });

    diffEditor.setModel({
        original: originalModel,
        modified: modifiedModel
    });

    // Adjust editor height to fit content
    function updateEditorHeight() {
        var contentHeight = Math.max(
            diffEditor.getOriginalEditor().getContentHeight(),
            diffEditor.getModifiedEditor().getContentHeight()
        );
        document.getElementById('objectchange-diff-viewer').style.height = contentHeight + 'px';
        diffEditor.layout();
    }

    // Initial height update
    updateEditorHeight();
});
