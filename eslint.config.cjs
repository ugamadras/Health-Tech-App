module.exports = [
  {
    files: ["services/app-api/src/app_api/static/**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "script",
      globals: {
        alert: "readonly",
        DataTransfer: "readonly",
        document: "readonly",
        fetch: "readonly",
        FileReader: "readonly",
        clearInterval: "readonly",
        setInterval: "readonly",
        Number: "readonly",
        Promise: "readonly",
        String: "readonly",
      },
    },
    rules: {
      "no-constant-condition": "error",
      "no-undef": "error",
      "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    },
  },
];
