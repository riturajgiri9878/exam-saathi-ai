# Version 4.1 - Geography Visual and Evidence Fix

## What changed

- Political-geography words such as `landlocked`, `country`, `border` and `coastline`
  now route to Geography.
- Doubly-landlocked questions receive a labelled Uzbekistan diagram containing all five
  landlocked neighbours and the open-ocean access rule.
- A trailing `Answer:` supplied with the question is hidden on the recall page.
- Recognised evidence-backed packs list readable World Bank and government sources.
- Packs without attached evidence say `Reviewed explanation`, not `Verified explanation`.
- The PDF diagram is compressed before embedding, reducing download size without losing
  readable labels.
- Political-geography prompts now check inland seas, neighbours, spatial analogies and
  route examples more carefully.

## Expected Uzbekistan result

The core answer is Uzbekistan. The visual identifies Kazakhstan, Kyrgyzstan, Tajikistan,
Afghanistan and Turkmenistan as landlocked neighbours. The explanation distinguishes the
Caspian Sea from an open-ocean coast and does not use a land/water-reversing island analogy.

## Honest boundary

The app uses deterministic routing and an independent reviewer to reduce errors, but no
AI system can guarantee every factual answer. Source links remain visible so students can
verify important claims.
