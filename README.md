# TPM Course Flow Website

This is a static website that explains the TPM bootcamp as one connected lifecycle.

## Files

- index.html
- styles.css
- script.js
- data/course_source_digest.json
- data/course_source_digest.md
- tools/scan_course_sources.py

## Re-Scan Course Sources (Week/Day)

To refresh source-grounded content from TPM Workshop files:

- Run: c:/Users/gs1-sangeethanc/Desktop/TPM/BootCamp/.venv/Scripts/python.exe tools/scan_course_sources.py

This reads Week 1 -> Week 4 day-by-day and updates:

- data/course_source_digest.json
- data/course_source_digest.md

## Run Locally (Option 1: Direct Open)

Double-click index.html to open it in your browser.

Note: direct file mode may block JSON loading in some browsers. If the source scan section is empty, use localhost mode below.

## Run Locally (Option 2: Localhost)

From this folder, run:

- Open PowerShell in this folder.
- Run: python -m http.server 8080

Then open:

- http://localhost:8080

## Publish To GitHub Pages

1. Create a GitHub repo and push these files.
2. Go to Settings -> Pages.
3. Under Build and deployment, choose Deploy from a branch.
4. Select branch main and folder / (root), then Save.
5. Wait for deployment and open the provided Pages URL.

## Notes

- The page is responsive for desktop and mobile.
- It uses semantic HTML and keyboard-friendly patterns.
- You can extend sections for later weeks as your bootcamp progresses.
