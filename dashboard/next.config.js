/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingIncludes: {
    "/api/dashboard": ["./template/**/*"],
  },
  webpack: (config) => {
    config.module.rules.push({
      test: /dashboard_template\.html$/,
      type: "asset/source",
    });
    return config;
  },
};

module.exports = nextConfig;
