import type { NextConfig } from 'next';
import dotenv from 'dotenv';
import path from 'node:path';

// Keep provider and LiveKit secrets in the repository root.
dotenv.config({ path: path.resolve(__dirname, '../.env') });

const nextConfig: NextConfig = {
  /* config options here */
};

export default nextConfig;
