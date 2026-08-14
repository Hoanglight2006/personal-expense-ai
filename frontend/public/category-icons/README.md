# Category icon assets

The category UI now imports the local PNG assets from `src/assets` through Vite.
The whitelist and per-image visual scale are defined in
`src/constants/categoryIcons.js`. If an image cannot load, `CategoryIcon` keeps a
text fallback so the card layout remains usable.
