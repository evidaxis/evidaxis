declare module '*.astro' {
  // Container tests consume the same compiled component factory as Astro's renderer.
  const component: Parameters<import('astro/container').experimental_AstroContainer['renderToString']>[0];
  export default component;
}
