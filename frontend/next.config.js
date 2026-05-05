/** @type {import('next').NextConfig} */
const nextConfig = {
  // Configuração para servir arquivos estáticos corretamente
  assetPrefix: '',
  // Garantir que o CSS seja processado
  compiler: {
    styledComponents: true, // se você usa styled-components
  },
  // Configuração para desenvolvimento no Docker
  webpackDevMiddleware: config => {
    config.watchOptions = {
      poll: 1000,
      aggregateTimeout: 300,
    }
    return config
  },
}

module.exports = nextConfig