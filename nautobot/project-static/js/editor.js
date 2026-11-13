/**
 * Monaco Editor wrapper for embedding in any page.
 * 
 * Configuration via data attributes:
 * @param {string} data-mode - Set to 'diff' for diff viewer, omit for standard editor
 * @param {string} data-lang - Language syntax (json, yaml, xml, text)
 * @param {string} data-value - Initial content for standard editor
 * @param {string} data-original - Original content for diff viewer (requires data-mode="diff")
 * @param {string} data-modified - Modified content for diff viewer (requires data-mode="diff")
 * @param {string} data-options - JSON string of Monaco editor options to merge with base config
 * 
 * Example Usage:
 * 
 * Diff Viewer:
 * <div class="nb-editor-container"
 *      data-mode="diff"
 *      data-original="{{ diff_removed }}"
 *      data-modified="{{ diff_added }}"
 *      data-lang="json">
 * </div>
 * 
 * Standard Editor:
 * <div class="nb-editor-container"
 *      data-lang="yaml"
 *      data-value="key: value"
 *      data-options='{"readOnly": false}'>
 * </div>
 *
 * Containers present at page load are initialized automatically. Containers added later
 * (for example in a modal or an AJAX-loaded tab) must be initialized explicitly:
 *
 *   const editor = await window.nb.editor.create(host);
 *   ...
 *   window.nb.editor.dispose(host);
 */
;(function(window, document, undefined) {
  'use strict';

  const MONACO_BASE = window.nautobot_static_url + 'monaco-editor-0.52.2';

  class Editor {
      // Editor instances keyed by host element, so that a host can be disposed or re-initialized later
      static _instances = new WeakMap();

      // Base configuration for all editor instances
      static BASE_COMMON = {
          automaticLayout: true,
          scrollBeyondLastLine: false,
          lineDecorationsWidth: 0,
          lineNumbers: 'off',
          wordWrap: 'off',
          renderWhitespace: 'none',
          guides: { 
              indentation: false,
              highlightActiveIndentation: false,
              bracketPairs: false
          },
          readOnly: true,
          contextmenu: false,
          matchBrackets: 'never',
          accessibilitySupport: 'auto',
          minimap: { enabled: false },
          renderLineHighlight: 'none',
          hideCursorInOverviewRuler: true,
          overviewRuler: {
              border: false,
              lanes: 0,
              renderOverviewRuler: false
          },
          scrollbar: {
              useShadows: false,
              verticalScrollbarSize: 8,
              horizontalScrollbarSize: 8,
              alwaysConsumeMouseWheel: false,
              arrowSize: 0,
              handleMouseWheel: true
          },
      };

      // Additional configuration for diff viewer mode
      static BASE_DIFF = {
          enableSplitViewResizing: false,
          renderSideBySide: true,
          useInlineViewWhenSpaceIsLimited: false
      };

      /** Creates a new Editor instance, ensuring Monaco is loaded before initialization. */
      static async create(host) {
          await Editor.loadMonaco();
          // Re-initializing a host replaces its existing editor instead of stacking a second one
          Editor.disposeHost(host);
          const instance = new Editor(host);
          Editor._instances.set(host, instance);
          return instance;
      }

      /** Disposes the Editor instance attached to the given host element, if there is one. */
      static disposeHost(host) {
          Editor._instances.get(host)?.dispose();
      }

      /** Initializes shared Monaco Editor environment, ensuring only one initialization occurs. */
      static async loadMonaco() {
          if (window.monaco) return;

          // Create worker environment with blob URL wrapper for CORS
          const createWorkerEnv = () => {
              const workerPath = `${MONACO_BASE}/vs/base/worker/workerMain.js`;
              const absoluteWorkerPath = new URL(workerPath, window.location.origin).href;

              // Create cached blob URL for all workers
              if (!window._monacoWorkerUrl) {
                  const workerCode = `
                      self.MonacoEnvironment = { 
                          baseUrl: '${new URL(MONACO_BASE, window.location.origin).href}'
                      };
                      importScripts('${absoluteWorkerPath}');
                  `;
                  
                  window._monacoWorkerUrl = URL.createObjectURL(
                      new Blob([workerCode], { type: 'text/javascript' })
                  );
              }

              return { 
                  getWorkerUrl: () => window._monacoWorkerUrl
              };
          };

          // Load Monaco via AMD, reusing existing promise if pending
          window._monacoLoaderPromise ||= new Promise((resolve, reject) => {
              const script = document.createElement('script');
              script.src = `${MONACO_BASE}/vs/loader.js`;
              script.crossOrigin = 'anonymous';
              
              script.onload = () => {
                  require.config({
                      paths: { 
                          vs: `${MONACO_BASE}/vs`
                      }
                  });
                  
                  window.MonacoEnvironment = createWorkerEnv();
                  require(['vs/editor/editor.main'], resolve, reject);
              };
              
              script.onerror = reject;
              document.head.appendChild(script);
          });

          await window._monacoLoaderPromise;
      }

      /** Constructs a new Editor instance with configuration from host element. */
      constructor(host) {
          this._host = host;
          this._editor = null;
          this._resizeObserver = null;

          // Destructure with safety
          const { mode, lang, value, original, modified, options } = host.dataset;
          
          this._config = {
              isDiff: mode === 'diff',
              language: lang || 'text',
              theme: document.documentElement.dataset.theme === 'dark' ? 'vs-dark' : 'vs',
              value: value || '',
              original: original || '',
              modified: modified || '',
              options: {
                  ...JSON.parse(options || '{}')  // User overrides
              }
          };

          this.init();
      }

      /** Initializes editor with configured options and sets up event listeners. */
      init() {
          const { theme, language, isDiff, options } = this._config;
          
          const editorOptions = {
              ...Editor.BASE_COMMON,  // Use static property
              ...(isDiff ? Editor.BASE_DIFF : {}),  // Use static property
              ...options
          };
          
          if (this._config.isDiff) {
              this._createDiffEditor({ theme, language, ...editorOptions });
          } else {
              this._createStandardEditor({ theme, language, ...editorOptions });
          }

          this._setupResize();
          this._setupContentHeightListener();
      }

      /** Creates a standard Monaco editor with the configured value and options. */
      _createStandardEditor(options) {
          this._editor = monaco.editor.create(this._host, {
              ...options,
              value: this._config.value
          });
      }

      /** Creates a Monaco diff editor with original and modified content models. */
      _createDiffEditor(options) {
          this._editor = monaco.editor.createDiffEditor(this._host, options);
          const { language, original, modified } = this._config;
          this._editor.setModel({
              original: monaco.editor.createModel(original, language),
              modified: monaco.editor.createModel(modified, language)
          });
      }

      /** Sets up a debounced resize observer to update editor layout. */
      _setupResize() {
          let resizeTimeout;
          this._resizeObserver = new ResizeObserver(() => {
              // Add debouncing for better performance with multiple editors
              if (resizeTimeout) clearTimeout(resizeTimeout);
              resizeTimeout = setTimeout(() => {
                  this._editor?.layout();
                  this._updateEditorHeight();
              }, 100);
          });
          this._resizeObserver.observe(this._host);
      }

      /** Registers listeners to update editor height when content size changes. */
      _setupContentHeightListener() {
          // Store listeners for cleanup
          this._contentListeners = [];
          const update = () => this._updateEditorHeight();

          if (this._config.isDiff) {
              this._contentListeners.push(
                  this._editor.getOriginalEditor().onDidContentSizeChange(update),
                  this._editor.getModifiedEditor().onDidContentSizeChange(update)
              );
          } else {
              this._contentListeners.push(
                  this._editor.onDidContentSizeChange(update)
              );
          }
      }

      /** Updates editor container height based on content and max-height constraints. */
      _updateEditorHeight() {
          if (!this._editor) return;

          const getHeight = e => e.getContentHeight() + 5;
          let contentHeight;

          if (this._config.isDiff) {
              contentHeight = Math.max(
                  getHeight(this._editor.getOriginalEditor()),
                  getHeight(this._editor.getModifiedEditor())
              );
          } else {
              contentHeight = getHeight(this._editor);
          }

          // Get max-height from CSS (if set)
          const maxHeight = parseInt(getComputedStyle(this._host).maxHeight, 10);
          if (!isNaN(maxHeight)) {
              contentHeight = Math.min(contentHeight, maxHeight);
          }

          this._host.style.height = `${contentHeight}px`;
          this._editor.layout();
      }

      /** Cleans up editor instance, models, and event listeners. */
      dispose() {
          if (!this._editor) return;

          // Dispose content size listeners
          this._contentListeners?.forEach(listener => listener.dispose());
          this._contentListeners = null;

          // Cleanup editor; it must be disposed before its models, or Monaco reports an error
          const model = this._editor.getModel();
          this._editor.dispose();
          this._resizeObserver?.disconnect();
          Editor._instances.delete(this._host);

          // Dispose models safely
          if (this._config.isDiff) {
              model?.original?.dispose();
              model?.modified?.dispose();
          } else {
              model?.dispose();
          }

          // Clear references
          [this._editor, this._resizeObserver, this._host, this._config] = [];
      }
  }

  /**
   * Initializes an editor in the given `.nb-editor-container` element, loading Monaco first if needed.
   * Resolves with the Editor instance, or with null (and an error message in the host) on failure.
   */
  async function createEditor(host) {
      try {
          return await Editor.create(host);
      } catch (error) {
          host.textContent = 'Editor initialization failed';
          console.error('Monaco error:', error);
          return null;
      }
  }

  // Public API, for content that is inserted into the page after it has loaded
  window.nb ??= {};
  window.nb.editor = {
      create: createEditor,
      dispose: (host) => Editor.disposeHost(host),
  };

  // Initialize the editors that are present at page load
  document.addEventListener('DOMContentLoaded', () => {
      document.querySelectorAll('.nb-editor-container').forEach((host) => createEditor(host));
  });
})(window, document);
