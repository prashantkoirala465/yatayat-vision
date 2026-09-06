import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // a standalone build only bundles the runtime deps a request actually
  // needs (not the full node_modules tree) - keeps the docker image lean
  output: "standalone",
};

export default nextConfig;
