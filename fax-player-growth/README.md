# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type aware lint rules:

- Configure the top-level `parserOptions` property like this:

```js
export default {
  // other rules...
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    project: ['./tsconfig.json', './tsconfig.node.json'],
    tsconfigRootDir: __dirname,
  },
}
```

- Replace `plugin:@typescript-eslint/recommended` to `plugin:@typescript-eslint/recommended-type-checked` or `plugin:@typescript-eslint/strict-type-checked`
- Optionally add `plugin:@typescript-eslint/stylistic-type-checked`
- Install [eslint-plugin-react](https://github.com/jsx-eslint/eslint-plugin-react) and add `plugin:react/recommended` & `plugin:react/jsx-runtime` to the `extends` list

## Embed do fax_portal / SquashEngine

```html
<!-- Stránka fax_portal: /squash-engine/player-growth -->
<link rel="stylesheet" href="/static/squash-engine-player-growth.css" />
<div id="player-growth" style="min-height:600px"></div>
<script src="/static/squash-engine.iife.js"></script>
<script>
  // Mountnutí widgetu
  window.SquashEngine.mountPlayerGrowth("#player-growth");
</script>
```

Stačí zkopírovat soubory z `dist/` do `fax_portal/public/static/` (nebo jakýkoli statický hosting).
Alternativa: použij `<iframe src="/static/index.html">` a načti standalone build.
