declare module 'occt-import-js' {
  type OcctModule = {
    ReadStepFile: (content: Uint8Array, params: object | null) => Promise<unknown> | unknown
  }
  const factory: () => Promise<OcctModule>
  export default factory
}
