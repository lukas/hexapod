import { readFile } from 'node:fs/promises'
import { readServerInfo } from '../../hub/hub'
import { optionString, type CliOptions } from '../../hub/cliShared'
import type { CatalogItem } from '../../core/catalogModel'
import { printJson } from '../cliFormat'

export const catalogCommand = async (positional: string[], options: CliOptions) => {
  const command = positional[0] ?? 'list'
  if (!['list', 'show', 'upsert'].includes(command)) {
    throw new Error('Usage: buildviz catalog list|show <id>|upsert <file.json> [--url <hub>] [--json]')
  }
  const configured = optionString(options, 'url') ?? (await readServerInfo())?.baseUrl
  if (!configured) throw new Error('No hub found. Start buildviz hub --detach or pass --url <hub>.')
  const base = new URL(configured)
  if (!['http:', 'https:'].includes(base.protocol)) throw new Error('Hub URL must use HTTP or HTTPS.')
  const headers: Record<string, string> = { Accept: 'application/json' }
  const apiKey = optionString(options, 'api-key') ?? process.env.BUILDVIZ_API_KEY
  if (apiKey) headers['X-API-Key'] = apiKey
  const request = async (pathname: string, body?: unknown) => {
    const response = await fetch(new URL(pathname, base), {
      method: body === undefined ? 'GET' : 'POST',
      headers: { ...headers, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      signal: AbortSignal.timeout(30_000),
    })
    if (!response.ok) throw new Error(`Catalog request failed (${response.status}): ${await response.text()}`)
    return response.json()
  }
  const status = await request('/__buildviz/status') as { service?: string }
  if (status.service !== 'buildviz-hub') throw new Error('The selected server is not a BuildViz hub.')
  if (command === 'upsert') {
    if (!positional[1]) throw new Error('catalog upsert requires a JSON file containing an item, array, or {items:[...]}.')
    const input = JSON.parse(await readFile(positional[1], 'utf8'))
    const items = Array.isArray(input) ? input : input.items ?? [input]
    const result = await request('/__buildviz/catalog', { items })
    if (options.json) printJson(result)
    else console.log(`Saved ${items.length} catalog item(s).`)
    return
  }
  const catalog = await request('/__buildviz/catalog') as { schema: number; items: CatalogItem[] }
  if (command === 'show') {
    const item = catalog.items.find((entry) => entry.id === positional[1] || entry.aliases?.includes(positional[1]))
    if (!item) throw new Error(`Catalog item not found: ${positional[1] ?? '(missing id)'}`)
    printJson(item)
    return
  }
  const query = (optionString(options, 'search') ?? '').toLowerCase()
  const kind = optionString(options, 'kind')
  const collection = optionString(options, 'collection')
  const parent = optionString(options, 'parent')
  const items = catalog.items.filter((item) =>
    (options.archived || item.status !== 'archived') &&
    (!kind || item.kind === kind) && (!collection || item.collection === collection) &&
    (!parent || item.parentId === parent) &&
    (!query || `${item.id} ${item.name} ${item.description}`.toLowerCase().includes(query)),
  )
  if (options.json) printJson({ schema: catalog.schema, items })
  else {
    for (const item of items) {
      console.log(`${item.name} [${item.kind}, ${item.status}] — ${item.id}`)
      console.log(`  ${item.description}`)
    }
    if (!items.length) console.log('No matching catalog items.')
  }
}
