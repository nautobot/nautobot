import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import importPlugin from 'eslint-plugin-import';
import globals from 'globals';

export default defineConfig([
  {
    languageOptions: {
      ecmaVersion: 'latest',
      globals: { ...globals.browser, $: 'readonly' },
    },
    plugins: { importPlugin, js },
    extends: [importPlugin.flatConfigs.recommended, 'js/all'],
    rules: {
      camelcase: 'off', // Some of the names use snake case to stay consistent with their backend counterparts.
      'id-length': ['error', { exceptions: ['$', 'q'] }], // Prevent obscure one-char names but make some explicit exceptions.
      'import/order': ['error', { alphabetize: { order: 'asc' }, 'newlines-between': 'never' }], // Keep imports consistent.
      'max-lines': 'off',              // Code length and organization should be up to its author, not linter, to decide.
      'max-lines-per-function': 'off', // Ditto.
      'max-statements': 'off',         // Ditto.
      'no-empty-function': 'off', // No-op functions can be useful at times, they are not always signs of unthoughtful engineering.
      'no-inline-comments': 'off', // Inline comments are fine, sometimes it is better to keep them close to the code.
      'no-magic-numbers': 'off', // Magic numbers may be difficult to understand, but forcing their assignment to constants does not necessarily make things clearer either.
      'no-ternary': 'off', // Enable ternaries, they are valid JavaScript syntax after all.
      'no-undefined': 'off', // Explicit `undefined` does not always mean the same as `null` and is useful in its own way.
      'no-warning-comments': 'off', // Allow `TODO` and `FIXME` comments.
      'one-var': ['error', 'never'], // Require a separate `const` statement for each constant.
      'prefer-named-capture-group': 'off', // Regular expressions are difficult to read already, no need to clutter them with more nonsense.
      'require-unicode-regexp': 'off',     // Ditto.
      'sort-imports': 'off', // Disable this rule in favor of more sophisticated `eslint-plugin-import`.
    },
  },
]);
