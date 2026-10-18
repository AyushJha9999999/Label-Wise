import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  devIndicators: false,
  // Keep generated Next.js files out of the cloud-placeholder cache in OneDrive.
  distDir: ".next-local",
  webpack(config) {
    config.resolve.alias = {
      ...config.resolve.alias,
      "firebase/app$": path.resolve(
        process.cwd(),
        "node_modules/firebase/app/dist/esm/index.esm.js",
      ),
      "firebase/auth$": path.resolve(
        process.cwd(),
        "node_modules/firebase/auth/dist/esm/index.esm.js",
      ),
    };
    return config;
  },
};
export default nextConfig;
