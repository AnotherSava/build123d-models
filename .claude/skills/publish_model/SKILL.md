---
name: publish_model
description: Create model description and publish to Thingiverse and MakerWorld
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, WebSearch, WebFetch
---

**Reference**: See `.claude/skills/publish_model/PUBLISHING_NOTES.md` for platform-specific technical details (selectors, API quirks, file formats, folder structure).

1. **Identify model and read source code**
   - Ask what model to describe if not provided as input
   - Locate the model's Python source file (e.g. `src/sava/csg/build123d/models/other/markerholder.py`)
   - Read the source to understand dimensions, features, and structure
   - Ask user for a few keywords or a short description if the model name alone isn't descriptive enough

2. **Collect photos**
   - Create a `photo` subfolder inside the model's output folder (e.g. `models/other/marker_holder/photo/`)
   - Ask user for the cover photo in 4x3 format — copy it to `photo/cover_4x3.<ext>` (preserving original extension)
   - Ask user for the cover photo in 3x4 format — copy it to `photo/cover_3x4.<ext>`
   - Ask user for any additional photos — copy them to `photo/photo_01.<ext>`, `photo/photo_02.<ext>`, etc.

3. **Create output folder**
   - Create a `description` subfolder inside the model's output folder (e.g. `models/other/marker_holder/description/`)

4. **Research similar models**
   - First, use WebFetch to read descriptions and tags from models already published in this project (Thingiverse/MakerWorld links in `README.md`) - these are the primary reference for style and formatting
   - Then search for similar models by other authors using `.claude/skills/publish_model/scripts/web_search.py`:
     - `./venv/Scripts/python.exe .claude/skills/publish_model/scripts/web_search.py search "<keywords>" --platform both --max 5`
     - Note: this launches a visible browser (headless=False) to bypass Cloudflare — this is expected
     - Categories are scraped automatically from each model page in `Category > Subcategory` format (all platforms)
   - Use WebFetch to read 3-5 top external results from each platform, focusing on:
     - Tags/keywords used
     - What details they include that our own descriptions might be missing
   - `web_search.py fetch <url>` also extracts categories from all platforms
   - Save found similar models to `description/similar_models.txt` in the format:
     ```
     Name: <model name>
     Category: <category>
     URL: <model url>

     ```

5. **Write description (Thingiverse format)**
   - Come up with a model name for publishing (concise, descriptive, similar to names of similar models found in step 4)
   - Choose a Thingiverse category based on categories of similar Thingiverse models in `similar_models.txt`
   - Assemble a description based on the model's actual features and inspired by similar models
   - Save to `description/thingiverse.md` with structured header followed by description body:
     ```
     Name: <model name>
     Category: <category> > <subcategory>
     Tags: <comma separated tags based on similar Thingiverse models>

     <description body>
     ```
   - Description body formatting (use published models in this project as reference):
     - Summary is just the opening paragraph — no "Summary" header (Thingiverse already has one in the UI)
     - Section headers use `**bold**` markdown (e.g. `**Key Features**`), not plain text, not `#` headings
     - Typical sections: opening summary paragraph, **Key Features** (bullet points), variant/option sections if applicable, **Compatibility** (if applicable)
     - End with an italic call-to-action: `*Suggestions for improvements? Reach out — happy to refine the design.*`
     - Concise, practical tone

6. **User review**
   - Present the description to the user for feedback
   - Iterate on `description/thingiverse.md` until user is satisfied

7. **Create MakerWorld version**
   - Create `description/makerworld.md` with the same header format but MakerWorld-specific values:
     ```
     Name: <model name>
     Category: <category> > <subcategory>
     Tags: <comma separated tags based on similar MakerWorld models>

     <description body>
     ```
   - Choose a MakerWorld category:
     - Review categories of similar MakerWorld models in `similar_models.txt` (from step 4)
     - Present the most common category > subcategory pairs to the user, along with a recommended pick
     - The category must match an existing MakerWorld category (typed into autocomplete during upload)
   - Description body may differ from Thingiverse version (e.g. emojis for section headers, more visual layout)
   - Tags can differ from Thingiverse — use tags found on similar MakerWorld models

8. **Publish draft to Thingiverse**
   - Collect the list of files to upload:
     - Photos: `cover_4x3.*` and all `photo_*` files from the `photo/` subfolder
     - Model files: `bambu.3mf` from the model output folder and all `.stl` files from `stl/`
   - Present the full file list (photos + model files) to the user and ask for confirmation before uploading
   - Use `.claude/skills/publish_model/scripts/thingiverse.py` to create a draft:
     - `./venv/Scripts/python.exe .claude/skills/publish_model/scripts/thingiverse.py draft <description_dir> --photo-dir <photo_dir> --files <file1> <file2> ...`
     - Example: `./venv/Scripts/python.exe .claude/skills/publish_model/scripts/thingiverse.py draft models/other/marker_holder/description --photo-dir models/other/marker_holder/photo --files models/other/marker_holder/bambu.3mf models/other/marker_holder/stl/marker_holder.stl`
   - Photos are uploaded first (cover_4x3 first to become the cover image at rank 0, then additional photos in order)
   - Reads Name, Tags, and description body from `thingiverse.md`
   - Creates as unpublished draft — not publicly visible until manually published
   - Requires OAuth2 token — first run will open browser for login, token is saved to `.env` for reuse
   - Prerequisites: `THINGIVERSE_CLIENT_ID` and `THINGIVERSE_CLIENT_SECRET` in `.env` (register app at https://www.thingiverse.com/apps/create with redirect URL `http://localhost:3000/callback`)

9. **Publish draft to MakerWorld**
   - Use the same file list from step 8
   - Use `.claude/skills/publish_model/scripts/makerworld.py` to create a draft:
     - `./venv/Scripts/python.exe .claude/skills/publish_model/scripts/makerworld.py draft <description_dir> --photo-dir <photo_dir> --files <file1> <file2> ...`
     - Example: `./venv/Scripts/python.exe .claude/skills/publish_model/scripts/makerworld.py draft models/other/marker_holder/description --photo-dir models/other/marker_holder/photo --files models/other/marker_holder/bambu.3mf models/other/marker_holder/stl/marker_holder.stl`
   - Uses Playwright browser automation with a real Chrome profile (bypasses Cloudflare)
   - Reads Name, Category, Tags, and description body from `makerworld.md` (falls back to `thingiverse.md`)
   - Types category subcategory into the autocomplete and selects the first match
   - Uploads cover images (4:3 and 3:4), additional photos, Bambu 3MF, and STL files
   - Creates as draft — not publicly visible until manually published
   - Prerequisites: run `./venv/Scripts/python.exe .claude/skills/publish_model/scripts/makerworld.py login` first to authenticate (session persists in `.chrome_mw_profile/`)

10. **Update project README and description files**
    - Add or update the model entry in `README.md` under the appropriate section
    - Use the Thingiverse URL from step 8 and MakerWorld URL from step 9:
      ```
      - **Model Name** - Short description ([Thingiverse](https://www.thingiverse.com/thing:XXXXX), [MakerWorld](https://makerworld.com/en/models/XXXXX)).
      ```
    - If the model already exists in the README with *(work in progress)*, replace that entry
    - Add the uploaded URL to each description file as a `URL:` line after `Tags:`:
      - In `thingiverse.md`: `URL: https://www.thingiverse.com/thing:XXXXX`
      - In `makerworld.md`: `URL: https://makerworld.com/en/models/XXXXX`