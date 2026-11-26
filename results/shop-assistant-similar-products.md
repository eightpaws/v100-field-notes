<!-- curated: do not overwrite -->
# Assistant on similar products — 87.5 % on full names, 15 % on short ones

_Testing the weak spot of any shop search: 936 products where many differ by one word — "Primula Belarina, Pink Ice" versus "Pink Champagne", "Adenium, Multi-graft 17" versus "27". 58 groups of similar products were found, the largest with 43 variants._

## Three measurements, 40 questions each

| How the question was phrased | top-1 | top-5 |
|---|---|---|
| Full name: "tell me about Bougainvillea, Dauphine" | **87.5 %** | 100 % |
| Name without variety: "is Primula belarina in stock?" | **15.0 %** | **90.0 %** |
| Qualifier only: "is a rooted one available?" | 27.5 % | 37.5 % |

The third measurement is invalid: the query carries no product identity, only the word "rooted", and search correctly returns a general instruction page. That is a flaw in the test design, not in retrieval.

## What the second measurement actually shows

When a customer names the product but not the variety, exact top-1 collapses to 15 %, yet **the right variant is in the top five 90 % of the time**. Four misses out of forty: "Hellebore" resolved to "Hellebore Caucasian", "Adenium, Multi-graft 17" to "27", "Primula belarina, Pink Ice" to "Baltic Blue", "Violet set, Miniature 8" to "Bordered 8".

Conclusion: never pick a variety on the customer's behalf when they did not name one. The correct answer is to list the options.

## What was changed

The system prompt now requires that, when the data holds several varieties of one name and no variety was given, the assistant lists the options with price and stock instead of choosing. A context hint was added too: the assistant detects that the retrieved hits share a base name and appends "the data holds several varieties of this product".

Verification after the change: "is Primula belarina in stock?" answers "currently none of this variety is in stock", which is correct — all six Belarina varieties carry "in stock: no" in the data. "Is Adenium in stock?" answers that none of the varieties are available, also correct.

## How it was measured

The set is built from the assistant corpus automatically: group by the first part of the name before the comma, strip service qualifiers (starter, baby, rooted), pick a random product per group with a fixed seed. Scripts `confusion_test.py`, `confusion_nameonly.py`, `confusion_short.py` in `/srv/media/projects/shop-assistant`.

## Limits

- 40 questions, one shop. Misses are rare, so the confidence interval is wide.
- Only retrieval is measured; answer wording was not separately labelled.
- Name grouping is crude: "Violet set" and "Violet set Bordered" land in one group although they are different products.
