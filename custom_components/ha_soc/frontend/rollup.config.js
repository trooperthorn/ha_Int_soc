import { nodeResolve } from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";
import json from "@rollup/plugin-json";
import terser from "@rollup/plugin-terser";

export default {
  input: "src/ha-soc-panel.ts",
  output: {
    file: "dist/ha-soc-panel.js",
    format: "esm",
    inlineDynamicImports: true,
  },
  plugins: [
    nodeResolve({ browser: true }),
    typescript({ tsconfig: "./tsconfig.json" }),
    json(),
    terser(),
  ],
};
