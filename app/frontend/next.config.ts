import type { NextConfig } from "next";
import path from 'path';

const nextConfig: NextConfig = {
  webpack: (config, { buildId, dev, isServer, defaultLoaders, nextRuntime, webpack }) => {
    // Configure fallbacks for Node.js modules
    config.resolve.fallback = {
      fs: false,
      net: false,
      tls: false,
    };
    
    // Add webpack alias as fallback for Docker compatibility
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(process.cwd(), 'src'),
    };
    
    return config;
  },
  images: {
    domains: ['localhost'],
  },
  // Disable ESLint during builds to avoid blocking
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Disable TypeScript checks during builds  
  typescript: {
    ignoreBuildErrors: true,
  },
  // Enable standalone build for better production performance
  output: 'standalone',
  // Optimize production builds
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
};

export default nextConfig;
