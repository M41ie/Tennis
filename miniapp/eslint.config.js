export default [
  {
    files: ['**/*.js'],
    ignores: ['node_modules/**', 'dist/**'],
    languageOptions: {
      ecmaVersion: 12,
      sourceType: 'module',
      globals: {
        wx: false,
        getApp: false,
        Page: false,
        Component: false,
        App: false,
        module: false,
        require: false,
        test: false,
        expect: false,
        document: false,
        __dirname: false,
        setTimeout: false,
        getCurrentPages: false
      }
    },
    linterOptions: {
      reportUnusedDisableDirectives: true,
    },
    rules: {
      'no-unused-vars': 'warn',
      'no-undef': 'error'
    }
  }
];
