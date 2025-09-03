import forms from "@tailwindcss/forms";

export default {
  safelist: [{ pattern: /bg-(red|green|yellow|gray)-500/ }],
  theme: {
    extend: {}
  },
  plugins: [forms]
};
