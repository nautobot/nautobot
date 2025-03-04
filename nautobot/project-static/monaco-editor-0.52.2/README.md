# Monaco Editor Custom Build

Minimal Monaco Editor distribution optimized for JSON, YAML, and XML. Built for reduced bundle size while maintaining core functionality.

## Install

```bash
nautobot/project-static/monaco-editor-[VERSION]/
```

## Features

- Full Monaco editing experience
- JSON with language server support
- YAML and XML syntax support
- Core UI components and Codicon font
- Modern browser support

## Build

```bash
# Get latest version
VERSION=$(curl -s https://registry.npmjs.org/monaco-editor | jq -r '."dist-tags".latest')

# Download and extract
curl -O -L "https://registry.npmjs.org/monaco-editor/-/monaco-editor-$VERSION.tgz"
tar -xzf monaco-editor-*.tgz

# Setup directories
mkdir -p nautobot/project-static/monaco-editor-$VERSION/vs/{editor,language,basic-languages}
mkdir -p nautobot/project-static/monaco-editor-$VERSION/vs/base/{worker,browser/ui}

# Copy core files
cp package/min/vs/loader.js nautobot/project-static/monaco-editor-$VERSION/vs/
cp package/min/vs/editor/editor.main.js nautobot/project-static/monaco-editor-$VERSION/vs/editor/
cp package/min/vs/editor/editor.main.css nautobot/project-static/monaco-editor-$VERSION/vs/editor/

# Copy language files
mkdir -p nautobot/project-static/monaco-editor-$VERSION/vs/language/json
mkdir -p nautobot/project-static/monaco-editor-$VERSION/vs/basic-languages/{yaml,xml}
cp -r package/min/vs/language/json/* nautobot/project-static/monaco-editor-$VERSION/vs/language/json/
cp -r package/min/vs/basic-languages/yaml/* nautobot/project-static/monaco-editor-$VERSION/vs/basic-languages/yaml/
cp -r package/min/vs/basic-languages/xml/* nautobot/project-static/monaco-editor-$VERSION/vs/basic-languages/xml/

# Copy worker and UI
cp -r package/min/vs/base/worker nautobot/project-static/monaco-editor-$VERSION/vs/base/
mkdir -p nautobot/project-static/monaco-editor-$VERSION/vs/base/browser/ui/codicons/codicon
cp -r package/min/vs/base/browser/ui/codicons/codicon/* nautobot/project-static/monaco-editor-$VERSION/vs/base/browser/ui/codicons/codicon/
```

## Structure

```bash
nautobot/project-static/monaco-editor-0.52.2/
├── vs/
│   ├── base/
│   │   ├── worker/
│   │   │   └── workerMain.js
│   │   └── browser/ui/codicons/
│   ├── basic-languages/
│   │   ├── xml/
│   │   └── yaml/
│   ├── editor/
│   │   ├── editor.main.css
│   │   └── editor.main.js
│   ├── language/
│   │   └── json/
│   └── loader.js
```

## Development

- MIT License
- Supports Chrome, Firefox, Safari, Edge
- Externally maintained build

## Contributing

1. Update version numbers in README and paths
2. Test in target application
3. Verify language services work
