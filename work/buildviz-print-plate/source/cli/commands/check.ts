// `buildviz check` + `buildviz sweep`: static/spatial checks and the
// swept-pose (kinematics) validation envelope.
//
// The implementations live at the hub layer (hub/checkRun.ts) because the
// hub's MCP `check_build` tool runs the same orchestration server-side and
// hub -> cli is not a legal dependency edge (plans/repo-split.md).
export { checkBuild, sweepBuild } from '../../hub/checkRun'
