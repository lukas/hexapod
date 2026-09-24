#!/usr/bin/env node
import path from 'node:path'
import {
  inspectBuild,
  queryBuild,
  summarizeFeature,
  summarizePart,
} from '../core/buildvizCore'
import {
  billOfMaterials,
  identify,
  type CheckReport,
  type IdentifyQuery,
  type SweepReport,
} from '../checks/buildvizGeometry'
import {
  DEFAULT_VERSION_NAME,
} from '../hub/buildsIndex'
import {
  printBom,
  printCheck,
  printIdentify,
  printInspect,
  printJson,
  printPack,
  printPart,
  printQuery,
  printSweep,
  printUsage,
} from './cliFormat'
import {
  optionString,
  parseArgs,
} from '../hub/cliShared'
import { appendUsageEvent, summarizeUsage } from '../hub/usageLog'
import {
  HUB_DEFAULT_PORT,
  HUB_SERVICE,
  packageVersion,
  printHubStatus,
  pushAnalysisToHub,
  pushToHub,
  feedbackToHub,
  registerWithHub,
  runHubCommand,
  SERVE_DEFAULT_PORT,
  startLocalServer,
} from '../hub/hub'
import { apiEnvelope, buildViewerUrl, geometryFilters, highlightSpecFromOptions, loadBuild, makeLoadMesh, parseLooseVec3, parseNumberOption, resolveViewerBaseUrl, validateBuild } from './cliBuild'
import { documentationStatus, initBuild } from './commands/docsInit'
import { compatCommand } from './commands/compat'
import { checkBuild, sweepBuild } from './commands/check'
import { packBuild } from './commands/pack'
import { listAssets } from './commands/inspect'
import { printWiresHuman, summarizeWires } from './commands/wires'
import { browseVersions, cacheCommand, diffCommand, freezeBuild, historyCommand, migrateBuilds } from './commands/versionsCmd'
import { screenshotBuild } from './commands/viewer'
import { drawingCommand, massCommand, meshCommand, probeCommand, sectionCommand, sliceCommand, thicknessCommand } from './commands/queryGeometry'
import { pushStlCommand } from './commands/pushStl'
import { catalogCommand } from './commands/catalog'



const knownCommands = new Set([
  'assets',
  'bom',
  'cache',
  'catalog',
  'check',
  'compat',
  'diff',
  'docs',
  'drawing',
  'daemon',
  'feature',
  'feedback',
  'freeze',
  'highlight',
  'history',
  'hub',
  'identify',
  'init',
  'inspect',
  'mass',
  'mesh',
  'migrate',
  'pack',
  'part',
  'probe',
  'push',
  'push-analysis',
  'push-step',
  'push-stl',
  'query',
  'register',
  'screenshot',
  'section',
  'serve',
  'send',
  'slice',
  'status',
  'sweep',
  'thickness',
  'usage',
  'validate',
  'versions',
  'wires',
])

// Grouped commands whose SECOND positional is a meaningful subcommand worth
// logging (e.g. `hub start`, `cache rm`, `probe region`, `mesh stats`). For
// every other command the first positional is a build dir / address / question
// and is deliberately NOT logged (it can contain paths or free text).
const SUBCOMMAND_COMMANDS = new Set(['hub', 'daemon', 'cache', 'catalog', 'probe', 'mesh'])

// Whitelist of flag NAMES we are willing to record in usage logs. We log names
// only (never values) and only these known flags, so a stray/typo flag or a
// value can never leak into the log. Kept in sync with the usage help above.
const LOGGABLE_FLAGS = new Set([
  'access', 'angle', 'assembly', 'assets-base-url', 'assets-dir', 'at', 'bed',
  'api-key', 'box', 'branch', 'build', 'build-id', 'bump', 'checks', 'clearance', 'density',
  'design-spec', 'detach', 'dry-run', 'emit', 'export', 'force', 'format',
  'gap-window', 'highlight-url', 'host', 'include-fasteners', 'instance', 'isolate', 'json',
  'keep', 'lan', 'local', 'local-point', 'margin', 'mating-tolerance',
  'max-pairs', 'max-span', 'max-upload-mb', 'message', 'metric', 'min', 'min-penetration', 'part-type', 'units',
  'min-thread-engagement', 'min-wall', 'name', 'no-assembleability',
  'no-autostart', 'no-default', 'no-fasteners', 'no-hidden', 'no-open', 'no-printability',
  'no-snapshot', 'out', 'part', 'plane', 'point', 'points', 'port', 'printer',
  'compare', 'compare-offset', 'display-name', 'project', 'range', 'region', 'res', 'samples', 'scene', 'search', 'sections',
  'source-branch', 'source-version',
  'set-default', 'set-default-branch', 'spacing', 'stl-dir', 'title', 'tolerance', 'upload-assets', 'url',
  'version', 'views', 'wall-samples', 'width', 'window', 'wire-clearance',
])

// Best-effort record that a known command ran, so a later "what's used vs.
// unused" audit is conclusive. Logs metadata ONLY: the command, an optional
// grouped subcommand, whitelisted flag NAMES (never their values), the buildviz
// version, and the cwd basename. Awaited (the append never throws) so the line
// is flushed before a short-lived CLI process exits.
const logCliInvocation = async (command: string, rest: string[]) => {
  const { positional, options } = parseArgs(rest)
  const subcommand = SUBCOMMAND_COMMANDS.has(command) ? positional[0] : undefined
  const flags = Object.keys(options)
    .filter((name) => LOGGABLE_FLAGS.has(name))
    .map((name) => `--${name}`)
    .sort()
  await appendUsageEvent({
    source: 'cli',
    command,
    ...(subcommand ? { subcommand } : {}),
    ...(flags.length > 0 ? { flags } : {}),
    version: packageVersion,
    cwd: path.basename(process.cwd()),
  })
}

const usage = `BuildViz LLM CLI

Usage:
  buildviz [<build-dir>] [--design-spec <file>] [--port 5173] [--host 127.0.0.1]
  buildviz serve [<build-dir>] [--design-spec <file>] [--port 5173] [--host 127.0.0.1]
  buildviz hub [start] [--detach] [--port 5183] [--host 127.0.0.1 | --lan] [--no-open] [--json]
    (--lan / a non-loopback --host bind the hub for teammates to VIEW; it then runs READ-ONLY:
     push, pack-export, register, and open-path are disabled. No auth — private-network trust only.)
  buildviz hub stop [--port 5183] [--host 127.0.0.1] [--json]
  buildviz hub status [--json]
  buildviz hub restart [--port 5183] [--host 127.0.0.1] [--json]
  buildviz register [<build-dir>] [--project <p>] [--build <b>] [--build-id <project/build>] [--design-spec <file>] [--name "Build name"] [--no-autostart] [--json]
  buildviz send [<build-dir>] [--project <p>] [--build <b>] [--build-id <project/build>] [--design-spec <file>] [--name "Build name"] [--no-autostart] [--json]
  buildviz push (-m <text> | --message <text>) [--project <p>] [--build <b>] [--branch <name>] [--version <name> | --bump] [--build-id <project/build>] [--scene <file>] [--name "Build name"] [--design-spec <file>] [--set-default] [--set-default-branch] [--no-default] [--no-snapshot] [--assets-base-url <url>] [--keep <n>] [--upload-assets] [--assets-dir <dir>] [--max-upload-mb <n>] [--no-autostart] [--json]
    (NEW VERSION BY DEFAULT: omitting --version is equivalent to --bump: pick the next free v<N>
     and make it default. --no-default keeps the current default. Published names are protected:
     changed content is rejected with a suggested next version; identical retries are unchanged.
     --no-snapshot cannot bypass this protection. --keep <n> explicitly prunes old versions.)
    (--branch targets (or creates) a BRANCH inside the build; each branch has its OWN version history
     and default version. Omitting --branch targets the build's default branch (usually "main").
     --set-default-branch makes the pushed branch the build default afterwards.)
    (--reason is STRONGLY RECOMMENDED: WHY the revision is needed — the previous version's problem
     or user request, affected parts, intended improvement, tradeoffs and remaining risks. Missing
     reasons produce a warning. Read feedback first and return afterward with validation evidence.)
    (-m/--message is REQUIRED: a short changelog note naming the version being created/bumped; it
     shows in the viewer's version dropdown, the current-version badge, the "new version" pill,
     diffs, and per-part history. Pushes without one are rejected — both by the CLI and by the
     hub's /__buildviz/push endpoint.)
    (--upload-assets ships each relative mesh file's BYTES so the pushed build is self-contained in
     the cache; assets are content-hashed (dedup across versions/builds), capped at 256MB by default.)
    (design_spec.yaml rides along automatically: with no --design-spec, a design_spec.yaml next to the
     pushed --scene file is attached. push and register WARN — in text output and as "warnings" in
     --json — when the spec is missing, doesn't cover every scene part type, has stale entries, or
     when geometry changed without a spec update. The spec records each part's PURPOSE;
     update it in the same change that alters geometry.)
  buildviz push-analysis <project/build> --name <slug> [--scene <file>] [--assets-dir <dir>] [--display-name <t>] [--message <text> | -m <text>] [--source-version <v>] [--source-branch <b>] [--max-upload-mb <n>] [--json]
    (attaches a NAMED analysis page (a derived scene: FEA stress fields, thermal maps, ...) to an
     EXISTING build instead of creating a separate build. Pages list at /builds/<id>/analyses.json,
     render via ?analysis=<slug>; changed results require a new slug, identical retries are unchanged. Relative
     mesh files are always uploaded so the page is self-contained.)
  buildviz push-stl <file.stl|file.step> [more ...] (-m <text> | --message <text>) [--project <p>] [--build <b>] [--build-id <project/build>] [--name "Display name"] [--part-type <type>] [--units mm|cm|m] [--linear-deflection <mm>] [--angular-deflection <rad>] [--version <name> | --bump] [--branch <name>] [--design-spec <file>] [--keep <n>] [--set-default] [--no-default] [--no-snapshot] [--max-upload-mb <n>] [--no-autostart] [--json]
  buildviz push-step <assembly.step>       # alias of push-stl; STEP solids become named, colored parts
    (one-command publish of loose STL file(s) as a self-contained hub build: composes a minimal
     scene.json — one identity-transform instance per file — and delegates to push --upload-assets.
     Defaults to --bump. Made for one-off printables (replacement brackets, experimental variants)
     so they get a viewer URL, drawing/probe/slice, and the printability check without hand-writing
     a scene. --build defaults to the first file's name; --part-type applies to every file.)
  buildviz feedback <project/build@version> [--branch <b>] [--url <hub-url>] [--json]
    (read the exact version's rationale and append-only findings BEFORE designing its successor.)
  buildviz feedback <project/build@version> --kind issue|validation|resolution|note --basis observed|user-report|hypothesis|test-result -m <finding> [--parts <comma-separated-ids>] [--evidence <text>] [--id <stable-id>] [--related-version <v>] [--related-feedback-id <id>] [--branch <b>] [--url <hub-url>] [--json]
    (record what went wrong on the version where it happened; never silently overwrite history.
     Resolutions require an original issue id, non-hypothesis basis and validation evidence.
     Reuse --id for an identical retry. A new version alone is not a verified fix.)
  buildviz status [--json]
  buildviz catalog list [--collection <id>] [--kind robot|assembly|view|study] [--parent <id>] [--search <text>] [--archived] [--url <hub>] [--json]
  buildviz catalog show <id> [--url <hub>]
  buildviz catalog upsert <file.json> [--url <hub>] [--json]
    (organize robots, assemblies, studies, and pinned inspection views without moving existing builds.
     Use BUILDVIZ_API_KEY for a protected hub; every saved view references an exact revision.)
  buildviz migrate [--json] [--dry-run]
  buildviz init [<build-dir>] [--stl-dir <dir>] [--name "Build name"] [--force] [--dry-run]
  buildviz docs [<build-dir>] [--json]
  buildviz usage [--json]
    (summarize ~/.buildviz/usage.jsonl: per-command + per hub-endpoint counts with first/last-seen.
     CLI invocations and hub /__buildviz/* + /builds requests are logged there, metadata only.)
  buildviz inspect <build|project/build[@version]> [--version <name>] [--json]
  buildviz compat [<project-dir>] [--json]
    (is a project BuildViz-compatible? checks scene.json manifest, STL meshes resolve, an up-to-date
     design_spec.yaml (a scene part with NO entry fails; stale/older-than-scene entries warn),
     ASSEMBLY.md, and BOM.md — per-requirement pass/warn/fail + an overall verdict.
     --json is the primary contract. See BUILDVIZ_COMPATIBILITY.md.)
  buildviz validate <build|project/build[@version]> [--version <name>] [--json]
  buildviz check <build|project/build[@version]> [--version <name>] [--tolerance <mm>] [--min-penetration <mm>] [--include-fasteners] [--max-pairs <n>] [--gap-window <mm>] [--min-wall <mm>] [--min-thread-engagement <mm>] [--mating-tolerance <mm>] [--wire-clearance <mm>] [--max-span <mm>] [--wall-samples <n>] [--checks <kind,kind>] [--no-printability] [--no-assembleability] [--access] [--emit] [--highlight-url] [--url <viewer>] [--json]
  buildviz wires <build|project/build[@version]> [--version <name>] [--json]
    (wiring summary from the scene's routes[]: per wire the kind, diameter, routed length vs budget,
     tightest bend radius vs minimum (6x OD default), anchors, and longest unsupported span. Geometry-
     aware wiring checks (obstruction, clearance) run in "check" as the default-on wire_* kinds.)
  buildviz sweep <build|project/build[@version]> [--version <name>] [--samples <n>] [--clearance <mm>] [--tolerance <mm>] [--min-penetration <mm>] [--include-fasteners] [--emit] [--url <viewer>] [--json]
  buildviz pack <build|project/build[@version]> [--version <name>] [--printer h2d|x1c] [--bed WxDxH] [--assembly <name>] [--angle 45] [--spacing <mm>] [--margin <mm>] [--emit] [--export] [--format 3mf|stl] [--out <dir>] [--url <viewer>] [--json]
  buildviz assets <build|project/build[@version]> [--version <name>] [--json]
  buildviz part <build|project/build[@version]> <part-type> [--version <name>] [--url <viewer>] [--json]
    (also prints a single-part deep link — ?part=<type>&isolate=1 — that opens the viewer with the
     part isolated and framed; --json includes it as viewUrl.)
  buildviz feature <build|project/build[@version]> <part-type> <feature-id> [--version <name>] [--json]
  buildviz query <build|project/build[@version]> "<question>" [--version <name>] [--json]
  buildviz versions [<project> | <project/build> | <build-dir>] [--json]
  buildviz history <build|project/build[@branch]> [<part-type>] [--branch <name>] [--json]
  buildviz history [--build <project/build>] --search "<terms>" [--json]
    (per-PART change history, derived from pushed version snapshots and kept in an append-only
     part_history.json ledger per branch — so it survives version-retention pruning. No part-type:
     one summary row per part (first seen / last changed / revision count). With a part-type: that
     part's full timeline — every version that changed its geometry (mesh content-hash), design-spec
     description, or instance count, with timestamps and push messages. --search matches part names
     + history text (descriptions, messages, versions; AND semantics) across every cached build when
     no build is given. Also on the hub: GET /__buildviz/part-history?build=..&part=..|&q=.. and the
     MCP tools get_part_history / search_part_history.)
  buildviz diff <project/build> <from-version> <to-version> [--json]
  buildviz highlight <build|project/build[@version]> [--version <name>] [--part <part-type>] [--point '[x,y,z]'] [--region 'x=a:b,y=c:d,z=e:f'] [--annotation "text"] [--json]
  buildviz screenshot <build|project/build[@version]> --part <part-type> --out <file> [--isolate] [--version <name>] [--url http://127.0.0.1:5173]
    (--isolate uses the single-part deep link — ?part=<x>&isolate=1 — so the shot shows ONLY that
     part, camera framed on it, instead of the whole build with the part selected.)
  buildviz probe points <build|project/build[@version]> --points '[[x,y,z],...]' [--part <type>] [--instance <id>] [--include-fasteners] [--version <name>] [--url <viewer>] [--json]
  buildviz probe region <build|project/build[@version]> --box 'x=a:b,y=c:d,z=e:f' [--samples <n>] [--part <type>] [--include-fasteners] [--version <name>] [--url <viewer>] [--json]
  buildviz slice <build|project/build[@version]> [--plane xy|yz|xz] [--metric area|min-thickness] [--at <c[,c...]>] [--range <axis=lo:hi[:step]>] [--res <mm>] [--min <mm>] [--part <type>] [--include-fasteners] [--version <name>] [--url <viewer>] [--json]
  buildviz thickness <build|project/build[@version]> [--plane auto|xy|yz|xz] [--sections <n>] [--res <mm>] [--min <mm>] [--part <type>] [--instance <id>] [--include-fasteners] [--version <name>] [--url <viewer>] [--json]
  buildviz mesh stats <build|project/build[@version]> [--part <type>] [--instance <id>] [--no-fasteners] [--version <name>] [--json]
  buildviz drawing <build|project/build[@version]> --part <type|meshId|instanceId> [--views front,right,top|all] [--no-hidden] [--out <file.svg>] [--version <name>] [--branch <name>] [--json]
  buildviz section <build|project/build[@version]> --plane <axis=v[,axis=v...]> [--part <types>] [--instance <ids>] [--include-fasteners] [--compare <build[@branch][@version]>] [--compare-offset x,y,z] [--window 'x=a:b,y=c:d'] [--title <text>] [--out <file.svg|file.png>] [--width <px>] [--version <name>] [--branch <name>] [--json]
    (true cross-section outlines on axis-aligned world planes, drawn as a labeled to-scale figure:
     one plane = filled part silhouettes (scene colors, even-odd holes); several planes (same axis)
     = per-plane colored outlines overlaid. --compare overlays a SECOND build/version's outlines
     dashed red — the before/after figure for design reviews; --compare-offset shifts it into the
     base build's frame when the scenes use different world frames. --out .png rasterizes;
     no --out prints SVG to stdout. Unlike "slice" (an occupancy grid for area/thickness metrics)
     this extracts exact mesh/plane contours to look at.)
  buildviz mass <build|project/build[@version]> [--density <g/cm3>] [--part <type>] [--no-fasteners] [--version <name>] [--branch <name>] [--json]
  buildviz identify <build|project/build[@version]> --instance <id> | --point x,y,z [--local x,y,z] [--version <name>] [--url <viewer>] [--json]
  buildviz bom <build|project/build[@version]> [--density <g/cm3>] [--part <type>] [--instance <id>] [--no-fasteners] [--version <name>] [--json]
  buildviz freeze <build-dir> (--version <name> | --bump) (-m <text> | --message <text>) [--set-default] [--no-default] [--no-snapshot] [--keep <n>] [--force] [--json]
    (the on-disk sibling of push: --bump auto-picks the next free v<N> (default), and overwriting the
     default in place first snapshots the prior default as a v<N> unless --no-snapshot. --keep <n> bounds growth.
     -m/--message is REQUIRED — a changelog note naming the frozen version, surfaced in the viewer;
     only a re-freeze of a version that already has a message may omit it (the note is kept).)
  buildviz cache ls [--json]
  buildviz cache rm <project/build> [--version <name>] [--json]

Data model — PROJECT / BUILD / BRANCH / VERSION:
  A PROJECT contains one or more BUILDS (assemblies); each build has one or more
  BRANCHES (like git branches), and each branch has its own NAMED VERSIONS. The
  canonical address is project/build@branch@version; the short form
  project/build@x resolves x as a branch when one matches, else as a version on
  the default branch (so pre-branch addresses keep working), e.g.
  spider/chassis@with-dome. Internally a build id is the "/"-joined slug
  "<project>/<build>" (a single-segment id like hexapod-2 is a project with one
  same-named build). Ids are slugified (spaces/capitals allowed on input), so
  --project "Spider Bot" --build Chassis -> spider-bot/chassis.

Versions (immutable snapshots on a branch):
  Each named version lives at <build>/versions/<name>/scene.json; the default
  version is also mirrored at the build root scene.json. One version is the
  default; "latest" is always an alias for the default. Omitting --version
  creates the next v<N> (v1 for a new build), just like --bump. You may also name it:
    buildviz push --project spider --build chassis --version with-dome -m "dome variant" --scene s.json
  pushing the SAME --version with changes is rejected (HTTP 409); an identical
  retry keeps its original bytes, message and timestamp. Use --branch for parallel
  design alternatives, --bump for each revision, and --no-default for reviews.
  --keep <n> explicitly prunes old versions; omitted keeps all. Use --set-default to make a named version the build
  default. diff compares two named versions of one build:
  buildviz diff spider/chassis main with-dome. On-disk builds use freeze --bump.
  (register/send point the hub at an on-disk directory and OVERWRITE its
  scene.json in place with NO versioning; push/freeze accumulate named versions.)

Branches (parallel lines of work, each with its own versions):
  A build's DEFAULT branch (usually "${DEFAULT_VERSION_NAME}") lives at the build root — exactly
  the layout above. Every other branch lives under <build>/branches/<name>/ with
  the same layout (scene.json = branch default, versions/<v>/ = named versions):
    buildviz push --project spider --build chassis --branch yoke-redesign --bump -m "yoke redesign" --scene s.json
  creates/updates the "yoke-redesign" branch without touching the default branch.
  Address a branch with @branch or @branch@version:
    buildviz check spider/chassis@yoke-redesign            # branch default version
    buildviz inspect spider/chassis@yoke-redesign@v3       # named version on the branch
    buildviz diff spider/chassis@main spider/chassis@yoke-redesign@v3
  --set-default-branch (with push) promotes the pushed branch to build default.
  The viewer gets a branch picker (&branch=<name> URL param) when a build has
  more than one branch.

Hub (the canonical cross-process target):
  The hub is the single server other processes/projects push to and read from.
  It runs on its OWN default port (${HUB_DEFAULT_PORT}) so it coexists permanently with a
  project's Vite dev server (npm run dev, default :${SERVE_DEFAULT_PORT}). --port overrides.
  Discover it via ~/.buildviz/server.json and VERIFY it with GET /__buildviz/status,
  which returns the signature { service: "${HUB_SERVICE}", version, pid, port, baseUrl, startedAt, builds }.
  Never assume a server is the hub from /builds/index.json alone -- a plain dev
  server serves that too. push/register/send/status all resolve + verify the hub
  this way, and push/register/send auto-start a detached hub on :${HUB_DEFAULT_PORT} if none is
  verified (unless --no-autostart). Resolve the hub from discovery, e.g.:
    node:   const i=JSON.parse(fs.readFileSync(os.homedir()+'/.buildviz/server.json'));
            const s=await (await fetch(i.baseUrl+'/__buildviz/status')).json();
            if(s.service!=='${HUB_SERVICE}') throw new Error('not a buildviz hub');
    python: i=json.load(open(os.path.expanduser('~/.buildviz/server.json')));
            s=requests.get(i['baseUrl']+'/__buildviz/status').json();
            assert s.get('service')=='${HUB_SERVICE}'
    curl:   curl -s "$(jq -r .baseUrl ~/.buildviz/server.json)/__buildviz/status" | jq -e '.service=="${HUB_SERVICE}"'

Examples:
  buildviz
  buildviz hub
  buildviz hub --detach
  buildviz hub status
  buildviz hub stop
  buildviz register . --project spider --build chassis
  buildviz push --project spider --build chassis -m "initial chassis" --scene scene.json   # lands as spider/chassis@${DEFAULT_VERSION_NAME}
  buildviz push --project spider --build chassis --version with-dome -m "dome variant" --scene scene.json   # parallel branch
  buildviz versions spider                 # browse builds + named versions under a project
  buildviz versions spider/chassis         # versions of one build (default marked)
  buildviz versions                        # browse every project -> build -> version
  buildviz diff spider/chassis main with-dome --json
  buildviz inspect spider/chassis@with-dome --json
  cat scene.json | buildviz push --project spider --build chassis -m "regenerated chassis"
  buildviz status
  buildviz init
  buildviz docs
  buildviz ../hexapod_2 --design-spec ../hexapod_2/design_spec.yaml --port 5174
  buildviz inspect public/builds/hexapod-2
  buildviz compat public/builds/hexapod-prototype --json   # is this project BuildViz-compatible?
  buildviz validate public/builds/hexapod-2 --json
  buildviz check public/builds/hexapod-2 --json
  buildviz check public/builds/hexapod-collision-chassis --highlight-url
  buildviz check public/builds/hexapod-collision-chassis --emit   # write buildviz_checks.json the viewer reads automatically
  buildviz check public/builds/hexapod-2 --access --json          # add the coarse assembly-access sweep
  buildviz check public/builds/hexapod-2 --checks watertight,thread_engagement --json  # only these kinds
  buildviz sweep public/builds/hexapod-motion-demo --emit   # worst-case swept-pose overlap envelope (needs scene joints[])
  buildviz pack public/builds/hexapod-prototype --printer x1c --json   # orient + pack parts onto 3D-printer plates
  buildviz pack public/builds/hexapod-prototype --assembly L0 --emit    # pack one leg + emit a viewer scene of the plates
  buildviz pack public/builds/hexapod-prototype --printer h2d --export                 # write Bambu-ingestible plate-1.3mf … plate-N.3mf (default <build>/plates/)
  buildviz pack public/builds/hexapod-prototype --export --format stl --out /tmp/plates # per-plate merged STL instead of 3MF
  buildviz part public/builds/hexapod-2 coxa_link --json
  buildviz feature public/builds/hexapod-2 coxa_link yaw_horn_pattern --json
  buildviz query public/builds/hexapod-2 "what dimensions define the coxa link?"
  buildviz highlight public/builds/hexapod-2 --part coxa_link --point '[0,0,0]' --annotation "Is this the right origin?"
  buildviz identify public/builds/hexapod-2 --point 12,0,8 --json        # world point in each enclosing part's local frame
  buildviz identify public/builds/hexapod-2 --instance coxa-L0 --local 0,0,0   # a part-local point back in world coords
  buildviz bom public/builds/hexapod-prototype --density 1.24 --json     # per-part-type count + volume + PLA mass estimate
  buildviz screenshot public/builds/hexapod-2 --part coxa_link --out screenshots/coxa.png

Inside the BuildViz repo, use npm run buildviz -- <args>.

BuildViz requires a valid scene.json and its referenced mesh assets such as STL files.
design_spec.yaml is optional: builds without one still register, serve, and render.
Run buildviz init to create missing starter guidance without overwriting existing files.
`


const main = async () => {
  const args = process.argv.slice(2)
  const [command, ...rest] = args
  if (command === '--help' || command === '-h') {
    console.log(usage)
    return
  }

  if (!command || command.startsWith('--') || !knownCommands.has(command)) {
    await startLocalServer(args)
    return
  }

  // Record this (resolved, known) invocation before dispatch so even long-running
  // foreground commands like `hub` are logged at start. Fire-and-forget + never
  // throws, so it cannot affect the command.
  await logCliInvocation(command, rest)

  if (command === 'usage') {
    const summary = await summarizeUsage()
    if (parseArgs(rest).options.json) {
      printJson(summary)
    } else {
      printUsage(summary)
    }
    return
  }

  if (command === 'serve') {
    await startLocalServer(rest)
    return
  }

  if (command === 'hub' || command === 'daemon') {
    await runHubCommand(rest)
    return
  }

  if (command === 'register' || command === 'send') {
    await registerWithHub(rest)
    return
  }

  if (command === 'push') {
    await pushToHub(rest)
    return
  }

  if (command === 'feedback') {
    await feedbackToHub(rest)
    return
  }

  if (command === 'push-analysis') {
    await pushAnalysisToHub(rest)
    return
  }

  if (command === 'push-stl' || command === 'push-step') {
    await pushStlCommand(rest)
    return
  }

  if (command === 'status') {
    await printHubStatus(rest)
    return
  }

  if (command === 'catalog') {
    const { positional, options } = parseArgs(rest)
    await catalogCommand(positional, options)
    return
  }

  if (command === 'init') {
    await initBuild(rest)
    return
  }

  if (command === 'docs') {
    documentationStatus(rest)
    return
  }

  const { positional, options } = parseArgs(rest)

  if (command === 'migrate') {
    await migrateBuilds(options)
    return
  }

  if (command === 'versions') {
    await browseVersions(positional[0], options)
    return
  }

  if (command === 'history') {
    await historyCommand(positional, options)
    return
  }

  if (command === 'freeze') {
    await freezeBuild(positional, options)
    return
  }

  if (command === 'cache') {
    await cacheCommand(positional, options)
    return
  }

  if (command === 'probe') {
    await probeCommand(positional, options)
    return
  }

  if (command === 'slice') {
    await sliceCommand(positional, options)
    return
  }

  if (command === 'thickness') {
    await thicknessCommand(positional, options)
    return
  }

  if (command === 'mesh') {
    await meshCommand(positional, options)
    return
  }

  if (command === 'drawing') {
    await drawingCommand(positional, options)
    return
  }

  if (command === 'section') {
    await sectionCommand(positional, options)
    return
  }

  if (command === 'mass') {
    await massCommand(positional, options)
    return
  }

  if (command === 'compat') {
    await compatCommand(positional, options)
    return
  }

  const buildDir = positional[0]
  if (!buildDir) throw new Error(`Missing build directory.\n\n${usage}`)

  if (command === 'diff') {
    await diffCommand(positional, options)
    return
  }

  const version = optionString(options, 'version')
  const branch = optionString(options, 'branch')
  const build = await loadBuild(buildDir, version, branch)

  if (command === 'inspect') {
    const inspected = inspectBuild(build.index)
    if (options.json) {
      printJson(apiEnvelope(true, build, `Inspected ${build.buildId}.`, inspected))
    } else {
      console.log(`Build: ${build.buildId} (version ${build.version})`)
      printInspect(inspected)
    }
    return
  }

  if (command === 'validate') {
    const result = await validateBuild(build)
    if (options.json) {
      printJson(result)
    } else {
      console.log(result.summary)
      if (result.errors.length > 0) console.log(`Errors: ${result.errors.length}`)
      if (result.warnings.length > 0) console.log(`Warnings: ${result.warnings.length}`)
    }
    return
  }

  if (command === 'check') {
    const viewerBaseUrl = await resolveViewerBaseUrl(options)
    const result = await checkBuild(build, options, viewerBaseUrl)
    if (options.json) {
      printJson(result)
    } else {
      printCheck(
        result.results as CheckReport & {
          highlightUrl: string | null
          sidecarPath?: string | null
          checkSummary?: { fail: number; warn: number; pass: number; total: number }
        },
      )
    }
    return
  }

  if (command === 'sweep') {
    const viewerBaseUrl = await resolveViewerBaseUrl(options)
    const result = await sweepBuild(build, options, viewerBaseUrl)
    if (options.json) {
      printJson(result)
    } else {
      printSweep(
        result.results as SweepReport & {
          checkSummary?: { fail: number; warn: number; pass: number; total: number }
          highlightUrl?: string | null
          sidecarPath?: string | null
        },
      )
    }
    return
  }

  if (command === 'pack') {
    const viewerBaseUrl = await resolveViewerBaseUrl(options)
    const result = await packBuild(build, options, viewerBaseUrl)
    if (options.json) {
      printJson(result)
    } else {
      printPack(
        result.results as Parameters<typeof printPack>[0],
      )
    }
    return
  }

  if (command === 'wires') {
    const result = summarizeWires(build)
    if (options.json) printJson(result)
    else printWiresHuman(result)
    return
  }

  if (command === 'assets') {
    const result = await listAssets(build)
    if (options.json) {
      printJson(result)
    } else {
      console.log(result.summary)
      const assets = result.results as Array<{ kind?: string; path?: string; exists?: boolean }>
      assets.forEach((asset) => {
        console.log(`- ${asset.kind ?? 'asset'}: ${asset.exists ? 'ok' : 'missing'} ${asset.path ?? ''}`)
      })
    }
    return
  }

  if (command === 'part') {
    const partType = positional[1]
    if (!partType) throw new Error('Missing part type.')
    const part = summarizePart(build.index, partType)
    if (!part) throw new Error(`No instances found for part type: ${partType}`)
    // Single-part deep link: the viewer isolates + frames the part on load.
    const partUrl = buildViewerUrl(build, await resolveViewerBaseUrl(options), {
      part: partType,
      isolate: '1',
    })
    if (options.json) {
      printJson(apiEnvelope(true, build, `Summarized part type ${partType}.`, { ...part, viewUrl: partUrl }))
    } else {
      printPart(part)
      console.log(`View (isolated): ${partUrl}`)
    }
    return
  }

  if (command === 'feature') {
    const partType = positional[1]
    const featureId = positional[2]
    if (!partType || !featureId) throw new Error('Usage: feature <build-dir> <part-type> <feature-id>')
    const feature = summarizeFeature(build.index, partType, featureId)
    if (!feature) throw new Error(`No feature found: ${partType}.${featureId}`)
    if (options.json) {
      printJson(apiEnvelope(true, build, `Summarized feature ${partType}.${featureId}.`, feature))
    } else {
      console.log(`${feature.partType}.${feature.featureId}: ${feature.label}`)
      if (feature.purpose) console.log(feature.purpose)
      if (feature.llmContext) console.log(feature.llmContext)
    }
    return
  }

  if (command === 'query') {
    const question = positional.slice(1).join(' ')
    if (!question) throw new Error('Missing query question.')
    const result = queryBuild(build.index, question)
    if (options.json) {
      printJson(apiEnvelope(true, build, result.answer, result))
    } else {
      printQuery(result)
    }
    return
  }

  if (command === 'highlight') {
    const highlights = highlightSpecFromOptions(options)
    const url = buildViewerUrl(
      build,
      await resolveViewerBaseUrl(options),
      {
        part: typeof options.part === 'string' ? options.part : undefined,
        instance: typeof options.instance === 'string' ? options.instance : undefined,
        highlight: JSON.stringify(highlights),
      },
    )
    const result = apiEnvelope(true, build, 'Generated BuildViz highlight URL.', { url, highlights })
    if (options.json) {
      printJson(result)
    } else {
      console.log(url)
    }
    return
  }

  if (command === 'screenshot') {
    const part = options.part
    const out = options.out
    if (typeof part !== 'string') throw new Error('Missing --part <part-type>.')
    if (typeof out !== 'string') throw new Error('Missing --out <file>.')
    await screenshotBuild(
      build, part, out, await resolveViewerBaseUrl(options), Boolean(options.isolate),
    )
    return
  }

  if (command === 'bom') {
    const filters = geometryFilters(options)
    const densityOpt = optionString(options, 'density')
    const densityGCm3 = densityOpt !== undefined ? parseNumberOption(densityOpt, 'density') : undefined
    const report = await billOfMaterials(build.index.manifest, {
      loadMesh: makeLoadMesh(build),
      partTypes: filters.partTypes,
      instanceIds: filters.instanceIds,
      // Fasteners are real BOM line items, so they are INCLUDED by default here;
      // --no-fasteners drops them (mirrors `mesh stats`).
      includeFasteners: !(options['no-fasteners'] ?? options.noFasteners),
      densityGCm3,
    })
    const summary =
      `${report.partTypeCount} part type(s) · ${report.instanceCount} part(s)` +
      (report.totals.massG !== null ? ` · ${report.totals.massG}g total` : ` · ${report.totals.volumeMm3}mm³ total`)
    if (options.json) {
      printJson(apiEnvelope(true, build, summary, report))
    } else {
      printBom(report)
    }
    return
  }

  if (command === 'identify') {
    const pointOpt = optionString(options, 'point')
    const localOpt = optionString(options, 'local', 'local-point')
    const instanceId = optionString(options, 'instance')
    if (!instanceId && !pointOpt) {
      throw new Error('Usage: buildviz identify <build> --instance <id> | --point x,y,z [--local x,y,z]')
    }
    const query: IdentifyQuery = {
      instanceId,
      worldPoint: pointOpt ? parseLooseVec3(pointOpt) : undefined,
      localPoint: localOpt ? parseLooseVec3(localOpt) : undefined,
    }
    const report = await identify(build.index.manifest, query, {
      loadMesh: makeLoadMesh(build),
      includeFasteners: true,
    })
    // A point highlight at the identified world location, for the viewer overlay.
    const primary = report.frames[0]
    const highlights = {
      points: [
        {
          point: report.worldPoint,
          instanceId: primary?.instanceId,
          color: primary?.insideSolid ? '#22c55e' : '#38bdf8',
          annotation:
            primary
              ? `${primary.partType} local [${primary.localPoint.join(', ')}]`
              : `world [${report.worldPoint.join(', ')}]`,
        },
      ],
    }
    const highlightUrl = buildViewerUrl(build, await resolveViewerBaseUrl(options), {
      highlight: JSON.stringify(highlights),
    })
    const summary = primary
      ? `World [${report.worldPoint.join(', ')}] = ${primary.partType} (${primary.instanceId}) local [${primary.localPoint.join(', ')}].`
      : `World [${report.worldPoint.join(', ')}] is not near any part.`
    if (options.json) {
      printJson(apiEnvelope(true, build, summary, { ...report, highlightUrl }))
    } else {
      printIdentify({ ...report, highlightUrl })
    }
    return
  }

  throw new Error(`Unknown command "${command}".\n\n${usage}`)
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error)
  console.error(message)
  if (message.includes('Executable doesn')) {
    console.error('Run `npx playwright install chromium` and retry.')
  }
  process.exitCode = 1
})
