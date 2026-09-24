// True when the viewer is loaded from the same machine as the (presumed) hub,
// i.e. a loopback host. Host-action affordances ("Open folder" in the Export
// panel, "Open STL folder" under the build dropdown) reveal a directory in the
// hub host's OS file manager, which is meaningless when pointed at a remote
// hub. Lives in its own module (not a component file) so react-refresh stays
// happy about component-only exports.
export const isLoopbackHost = (): boolean => {
  if (typeof window === 'undefined') return false
  const host = window.location.hostname
  return host === 'localhost' || host === '127.0.0.1' || host === '::1' || host === '[::1]' || host === ''
}
