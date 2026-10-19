---
name: feedback-text-one-object
description: Every exported text label is one object — join glyphs with TextSolid.connected() (0.01 mm pane) so a 3MF holds one object, not one per glyph
metadata:
  type: feedback
---

Text labels go out as ONE object: join their glyphs with `TextSolid.connected()` (`common/text.py`, a 0.01 mm pane below any layer height) so the 3MF holds one object rather than one per glyph. Where the text also engraves a part, cut with the bare glyphs and export the joined one; build the pane in the text's own frame before rotating; clip it to the surface the text stands on.

**Why:** the user expects every text label to load as a single object in the slicer (2026-10-17, planter tray: "all letters and labels should be one object"). build123d's Mesher writes one 3MF mesh object per solid, so disconnected glyphs otherwise arrive as dozens of objects. The helper had been removed as unused in January 2026 and was restored for this.

**How to apply:** any new or changed model that exports text — `plantertray.py` (`create_label`) and `poweradapters.py` (lid `text`, `socket types`) are the current examples.
