import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import { enumerateBuilds } from '../hub/buildsIndex'

// Serves /builds/index.json in dev and writes it into the build output so the
// viewer can discover available builds and versions. The buildviz local server
// provides its own index, signalled via BUILDVIZ_LOCAL_SERVE.
const buildsIndexPlugin = (): Plugin => {
  let root = process.cwd()
  let publicDir = path.join(process.cwd(), 'public')
  let outDir = 'dist'

  return {
    name: 'buildviz-builds-index',
    configResolved(config) {
      root = config.root
      publicDir = config.publicDir
      outDir = config.build.outDir
    },
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        const pathname = request.url ? new URL(request.url, 'http://localhost').pathname : ''
        if (pathname !== '/builds/index.json' || process.env.BUILDVIZ_LOCAL_SERVE) {
          next()
          return
        }

        void enumerateBuilds(path.join(publicDir, 'builds')).then((index) => {
          const body = JSON.stringify(index, null, 2)
          response.statusCode = 200
          response.setHeader('Content-Type', 'application/json')
          response.end(body)
        })
      })
    },
    async closeBundle() {
      const index = await enumerateBuilds(path.join(publicDir, 'builds'))
      const targetDir = path.resolve(root, outDir, 'builds')
      await mkdir(targetDir, { recursive: true })
      await writeFile(
        path.join(targetDir, 'index.json'),
        `${JSON.stringify(index, null, 2)}\n`,
        'utf8',
      )
    },
  }
}

// Vite rejects requests whose Host header is not a known hostname. When the
// hub is served through a reverse proxy / load balancer under a public
// hostname, allow it via BUILDVIZ_ALLOWED_HOSTS ("all", or a comma-separated
// hostname list).
const allowedHostsEnv = process.env.BUILDVIZ_ALLOWED_HOSTS
const allowedHosts =
  allowedHostsEnv === 'all' || allowedHostsEnv === 'true'
    ? (true as const)
    : allowedHostsEnv
      ? allowedHostsEnv.split(',').map((host) => host.trim()).filter(Boolean)
      : undefined

// https://vite.dev/config/
// The Vite root is viewer/ (this directory); the bundled example builds and
// other static assets stay at the repo-root public/, and the production build
// keeps landing in the repo-root dist/.
export default defineConfig({
  plugins: [react(), buildsIndexPlugin()],
  publicDir: '../public',
  build: { outDir: '../dist', emptyOutDir: true },
  ...(allowedHosts !== undefined ? { server: { allowedHosts } } : {}),
})
