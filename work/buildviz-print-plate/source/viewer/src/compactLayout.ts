// Single source of truth for the "compact controls" layout switch (the
// bottom-sheet mobile layout). Must stay in sync with the media query used in
// App.css: narrow screens (portrait phones) plus short touch screens
// (landscape phones), where the desktop sidebar is unusable.
export const compactLayoutQuery =
  '(max-width: 720px), ((max-height: 500px) and (pointer: coarse))'

export const isCompactLayout = () => window.matchMedia(compactLayoutQuery).matches

// Touch-first device (no reliable hover / right-click): drives the alternate
// interaction hints and the long-press context menu affordance.
export const isCoarsePointer = () => window.matchMedia('(pointer: coarse)').matches
