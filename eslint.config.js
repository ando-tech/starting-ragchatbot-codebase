import js from '@eslint/js';

export default [
    js.configs.recommended,
    {
        files: ['frontend/**/*.js'],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: 'script',
            globals: {
                document: 'readonly',
                window: 'readonly',
                console: 'readonly',
                fetch: 'readonly',
                marked: 'readonly',
                Date: 'readonly',
                Set: 'readonly',
            },
        },
        rules: {
            'no-unused-vars': 'warn',
            'no-console': 'warn',
            eqeqeq: 'error',
            'no-var': 'error',
            'prefer-const': 'warn',
        },
    },
];
