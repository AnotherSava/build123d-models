# Publishing Scripts — Technical Notes

Reference for `thingiverse.py`, `makerworld.py`, and `web_search.py`.

## File Format

Both `thingiverse.md` and `makerworld.md` use the same structured header:

```
Name: <model name>
Category: <category> > <subcategory>
Tags: <comma, separated, tags>

<description body in markdown>
```

Each platform has its own file because categories, tags, and description formatting may differ.

`similar_models.txt` uses a matching format:

```
Name: <model name>
Category: <category> > <subcategory>
URL: <model url>

```

Category is included for all platforms (MakerWorld, Printables, Thingiverse).

## Thingiverse (`thingiverse.py`)

- **API**: REST at `api.thingiverse.com`, OAuth2 bearer token.
- **Draft creation**: `POST /things/` with `is_wip: false` — stays unpublished without the WIP checkbox. Publishing is manual.
- **Category**: API expects a slug (e.g., `"organization"`, not `"Organization"`). Use the subcategory part of `Category > Subcategory`, lowercased, spaces to hyphens, `&` to `-and-`.
  - `GET /categories` only returns top-level categories; subcategory slugs must be derived from the display name.
- **File upload**: 3-step process — register via `/things/{id}/files`, upload to S3 URL, finalize via redirect URL. Images use the same endpoint; the first uploaded image becomes the cover (rank 0).
- **Token**: First run opens browser for OAuth2 flow. Token is saved to `.env` as `THINGIVERSE_ACCESS_TOKEN`. Requires `THINGIVERSE_CLIENT_ID` and `THINGIVERSE_CLIENT_SECRET` in `.env`.
- **Token exchange**: Server may return URL-encoded body instead of JSON — script handles both formats.

## MakerWorld (`makerworld.py`)

- **No public API** — uses Playwright browser automation with a real Chrome installation.
- **Cloudflare bypass**: Must use `channel="chrome"` (real Chrome, not Chromium) with a persistent profile directory (`.chrome_mw_profile/`) and `--disable-blink-features=AutomationControlled`.
- **Login**: `makerworld.py login` opens Chrome, navigates to makerworld.com, clicks "Log In" which redirects to Bambu Lab SSO (`bambulab.com/sign-in`). User completes login manually and closes the browser. Session persists in the Chrome profile directory.
- **Upload wizard** (3 steps):
  1. "Do you have a Bambu Studio file?" → select "Yes (earn extra...)" → Next
  2. Upload Bambu 3MF (first `input[type='file']`) + raw model files (second `input[type='file']`) → Next
  3. Model Information form → Save to draft
- **Step 3 form selectors**:
  - Title: `input[name='title']` (max 50 chars)
  - Category: `.modelCategory input[role='combobox']` — MUI Autocomplete, type subcategory to search, select from `[role='listbox'] [role='option']`
  - Tags: `.modelTags input[role='combobox']` — type each tag and press Enter
  - Description: `div.ck-content[role='textbox']` — CKEditor 5
  - Cover 4:3: `div.dropzone:has-text('4:3 Cover')` → child `input[type='file']`
  - Cover 3:4: `div.dropzone:has-text('3:4 Cover')` → child `input[type='file']`
  - Save: `button:has-text('Save to draft')`
- **CKEditor 5**: Must use `editorEl.ckeditorInstance.setData(html)` to set description. Setting `innerHTML` directly does NOT update CKEditor's internal data model — the description appears empty on save.
- **Cropper dialog**: Cover image uploads trigger a crop dialog (`MuiDialog-root` with cropper). Must dismiss via Confirm/Save/OK button before continuing to the next field.
- **Category autocomplete**: Search by subcategory only (e.g., type "Office" not "Household > Office") for a precise dropdown match.

## Web Search (`web_search.py`)

- **MakerWorld search**: Uses Chrome persistent profile (same as `makerworld.py`) to bypass Cloudflare. Visits each result page to extract category.
- **Thingiverse search**: Uses regular Chromium (no Cloudflare issues on search pages).
- **Printables**: `fetch` command works (for reading model details), but no `search` command implemented yet.
- **Category scraping selectors**:
  - MakerWorld: `a[href*='/en/3d-models/'].clickable` — breadcrumb links on model page
  - Printables: `a[href*='?category=']` — category links on model page
  - Thingiverse: JSON-LD `Product` schema in `<script type="application/ld+json">` — `data.category` field, comma-separated (converted to ` > ` format)
- **MakerWorld model pages**: Blocked by Cloudflare with fresh browsers. `fetch` command uses Chrome profile; `search` command also uses Chrome profile for visiting individual result pages.

## Photos

- `cover_4x3.*` — landscape cover, used on both Thingiverse (as main cover) and MakerWorld
- `cover_3x4.*` — portrait cover, MakerWorld only
- `photo_01.*`, `photo_02.*`, etc. — additional photos, uploaded to both platforms
- On Thingiverse: cover_4x3 is uploaded first (becomes rank 0 cover)
- On MakerWorld: both cover formats uploaded via separate dropzones, additional photos via "Add Photo" area

## Output Folder Structure

```
models/<group>/<model_name>/
├── bambu.3mf           # Bambu Studio project file
├── stl/                # Individual STL files
├── description/
│   ├── thingiverse.md  # Thingiverse listing (Name/Category/Tags + description)
│   ├── makerworld.md   # MakerWorld listing (Name/Category/Tags + description)
│   └── similar_models.txt  # Research: similar models with categories
└── photo/
    ├── cover_4x3.jpg   # Landscape cover
    ├── cover_3x4.jpg   # Portrait cover (MakerWorld)
    ├── photo_01.jpg     # Additional photo
    └── ...
```
