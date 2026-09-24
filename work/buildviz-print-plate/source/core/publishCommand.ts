const shellQuote = (value: string) => `'${value.replaceAll("'", "'\\''")}'`

// A suggested command, never executed by the viewer. Do not copy the viewed
// version into it: --bump lets the hub allocate safely, even if the menu is stale.
export const newVersionCommand = (buildId: string, branch: string) =>
  `npx buildviz push --build-id ${shellQuote(buildId)} --branch ${shellQuote(branch)} ` +
  '--bump --no-default --scene scene.json --upload-assets -m "Describe WHAT changed" ' +
  '--reason "Explain WHY: source-version problem or user request; intended improvement; tradeoffs and remaining risks"'
