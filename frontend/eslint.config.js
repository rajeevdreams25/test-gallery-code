import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'

export default [
  { ignores: ['dist/', 'node_modules/'] },

  js.configs.recommended,
  react.configs.flat.recommended,
  react.configs.flat['jsx-runtime'], // no `import React` needed with the new JSX transform
  reactHooks.configs.flat['recommended-latest'],

  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: globals.browser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    settings: {
      react: { version: 'detect' },
    },
    plugins: {
      'react-refresh': reactRefresh,
    },
    rules: {
      // This project passes plain props without the prop-types package.
      'react/prop-types': 'off',
      // Vite's fast refresh only works when a module exports components alone.
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      // Unused args are fine when they document a callback's signature.
      'no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^[A-Z_]' }],
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      eqeqeq: ['error', 'always', { null: 'ignore' }],
      'prefer-const': 'error',
    },
  },

  // Config files run in Node, not the browser.
  {
    files: ['*.config.js'],
    languageOptions: { globals: globals.node },
  },
]
