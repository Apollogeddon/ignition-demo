// @ts-check

import mdx from "@astrojs/mdx";
import sitemap from "@astrojs/sitemap";
import { defineConfig } from "astro/config";
import mermaid from "astro-mermaid";

// https://astro.build/config
export default defineConfig({
	site: "https://apollogeddon.github.io",
	base: "/ignition-demo",
	integrations: [mdx(), sitemap(), mermaid()],
});