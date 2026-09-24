import { isDeepStrictEqual } from 'node:util'
import { nextBumpVersion } from '../core/buildModel'

export const PUBLISH_POLICY = {
  versionReason: 'strongly-recommended',
  retrospectiveFeedback: 'append-only-exact-version',
  defaultMode: 'new-version',
  existingVersion: 'reject-changes',
  identicalRetry: 'unchanged',
  existingAnalysis: 'reject-changes',
} as const

export class VersionConflictError extends Error {
  readonly code = 'VERSION_ALREADY_EXISTS'
  readonly statusCode = 409
  readonly suggestedVersion: string
  readonly buildId: string
  readonly branch: string
  readonly version: string

  constructor(buildId: string, branch: string, version: string, versions: string[]) {
    const next = nextBumpVersion(versions)
    super(
      `${buildId}@${branch}@${version} is already published with different content. ` +
      'Published versions cannot be replaced. Remove --version and use --bump ' +
      `(next available: ${next}), or choose a new --version name. ` +
      'For HTTP pushes, omit version (or omit version and set bump:true). ' +
      'Use --no-default / setDefault:false to keep the current default. No version was changed.',
    )
    this.name = 'VersionConflictError'
    this.suggestedVersion = next
    this.buildId = buildId
    this.branch = branch
    this.version = version
  }
}

export class AnalysisConflictError extends Error {
  readonly code = 'ANALYSIS_ALREADY_EXISTS'
  readonly statusCode = 409

  constructor(buildId: string, slug: string) {
    super(`${buildId} analysis "${slug}" is already published with different content. ` +
      'Use a new --name (e.g. <new-version>-service-access) and --source-version <new-version>. ' +
      'The published analysis was not changed.')
    this.name = 'AnalysisConflictError'
  }
}

export const publishErrorResponse = (error: unknown) => ({
  status: error instanceof VersionConflictError || error instanceof AnalysisConflictError ? 409 : 400,
  body: {
    ok: false,
    error: error instanceof Error ? error.message : String(error),
    ...(error instanceof VersionConflictError ? {
      code: error.code, buildId: error.buildId, branch: error.branch, version: error.version,
      suggestedVersion: error.suggestedVersion, suggestion: { omitVersion: true, bump: true },
    } : error instanceof AnalysisConflictError ? { code: error.code } : {}),
  },
})

// Ignore JSON object-key order/formatting, but preserve every scene field and
// array order. Compare AFTER content-addressed uploads have rewritten mesh URLs.
export const sameScene = (previous: string, next: unknown): boolean => {
  try {
    return isDeepStrictEqual(JSON.parse(previous), JSON.parse(JSON.stringify(next)))
  } catch {
    return false
  }
}

// The hub is one writer. Serialize publish transactions, including allocation
// and the shared registry update, so concurrent --bump calls cannot reuse v<N>.
export const serialPublisher = () => {
  let tail: Promise<unknown> = Promise.resolve()
  return <T>(publish: () => Promise<T>): Promise<T> => {
    const result = tail.then(publish)
    tail = result.catch(() => undefined)
    return result
  }
}

// Feedback must not race a branch promotion or publish/retention transaction.
export const serializeBuildMutation = serialPublisher()
