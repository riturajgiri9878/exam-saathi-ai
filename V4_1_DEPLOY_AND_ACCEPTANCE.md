# Version 4.1 - One-Time Deployment and Acceptance Check

1. Extract the cumulative Version 4.1 ZIP.
2. Upload every file inside the extracted folder to the GitHub repository.
3. Commit with `Deploy Exam Saathi v4.1 geography visual fix`.
4. Wait for Render to show `Live`, then hard-refresh with `Ctrl + Shift + R`.
5. Confirm the header says `Version 4.1 - Source-Supported Geography Visuals`.

## Acceptance test

Ask: `Which country is doubly landlocked besides Liechtenstein? Answer: Uzbekistan`.

Confirm that:

- the subject is Geography;
- the question panel hides the supplied answer;
- the diagram names Uzbekistan and all five landlocked neighbours;
- the HTML has an animated relationship diagram;
- the PDF is static, readable and substantially smaller than the old 5.9 MB sample;
- the sources section lists the World Bank and Australian DFAT;
- no black rectangles, clipped text or missing pages appear.
