# Exam Saathi 3.2 — Previous Papers

## Added

- Extracts question-like items from verified PDF, image, text and HTML papers.
- Filters by the exact board/university, level, stream/degree, subject and
  syllabus profile entered by the user.
- Uses only papers marked `Previous exam paper` from the ten calendar years
  before the target exam year. Sample/practice papers are excluded.
- Ranks current-note topics by distinct matching years first and matched
  question count second.
- Shows matched question text with year, source filename and page.
- Shows target-year coverage and missing years.
- Saves extracted paper pages and metadata in a portable `.json.gz` catalog.
  The catalog can be restored after a Render deployment or browser restart,
  avoiding repeat OCR. Keep original paper files archived separately.

## Use it

1. Open `Previous Papers`.
2. Enter board/university, class/level, stream/degree, subject and the exact
   syllabus version/course code. Use the same values every time for one profile.
3. Enter the paper year and select `Previous exam paper` only for a genuine
   final/board/university paper. Upload files from that one year.
4. Press `Add and extract questions`. Repeat for each year.
5. Press `Save paper catalog` and download the `.json.gz` file.
6. Process the student's current notes in Secure Upload.
7. Return to Previous Papers, enter the same profile and target exam year, then
   press `Prioritize my uploaded notes`.
8. After an app restart, use `Restore saved catalog` before comparing.

## Evidence limits

The system does not ship copyrighted paper files and does not claim questions
are genuine based only on a filename. The uploader supplies and verifies paper
identity and syllabus metadata. OCR may split, merge or miss questions, so the
report says “question-like items” and links each result back to its source page.
Frequency supports revision priority; it is never presented as a guaranteed
future question.

All Indian boards and universities can be entered as profiles. A complete
national ten-year corpus still requires authorized source files for every
board/course/subject/year combination. This update provides the ingestion,
portable catalog and evidence analysis needed to build that corpus safely.

## Validation

Sixteen offline checks pass, including question extraction/deduplication,
ten-year filtering, sample-paper exclusion, topic reordering, source evidence,
catalog round-trip validation, Full Chapter resume and HTML export safety. All
Python modules compile.
