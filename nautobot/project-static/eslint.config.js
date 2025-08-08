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
      camelcase: 'off',
      'id-length': ['error', { exceptions: ['$', 'q'] }],
      'import/order': ['error', { alphabetize: { order: 'asc' }, 'newlines-between': 'never' }],
      'max-lines': 'off',
      'max-lines-per-function': 'off',
      'max-statements': 'off',
      'no-empty-function': 'off',
      'no-inline-comments': 'off',
      'no-magic-numbers': 'off',
      'no-ternary': 'off',
      'no-undefined': 'off',
      'no-warning-comments': 'off',
      'one-var': ['error', 'never'],
      'prefer-named-capture-group': 'off',
      'require-unicode-regexp': 'off',
      'sort-imports': 'off',
    },
  },
]);
