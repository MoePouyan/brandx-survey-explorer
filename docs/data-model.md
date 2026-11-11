# Data model reference

All tables are produced by `scripts/build_model.py`. Keys are text; `RespondentID` is a whole number.

## Respondents (dimension, 1,000 rows)

| Column | Description |
|---|---|
| `RespondentID` | Respondent key |
| `StudyGroup` / `StudyGroupOrder` | `Exposed` (1) or `Control` (2) |
| `Weight` | Rim weight by age, gender and province (`Weight_Final2`) |
| `Gender` / `Gender_Order` | From A2 |
| `AgeGroup` / `AgeGroup_Order` | 18-34, 35-54, 55+ |
| `Region` / `Region_Order` | Six regions |
| `CommunityType` / `CommunityType_Order` | Urban, suburban, rural (D9) |
| `ChipUsage` / `ChipUsage_Order` | Heavy or light chip user |
| `SnackPurchase` / `SnackPurchase_Order` | High or low snack purchase frequency |
| `ShoppingRole` / `ShoppingRole_Order` | Primary or non-primary household shopper |

Every label column is sorted by its `_Order` column.

## Questions (dimension, 14 rows)

| Column | Description |
|---|---|
| `QuestionID` | Key, for example `B2a` |
| `QuestionOrder` | Display order in the dropdown |
| `Section` | `A: Screening`, `B: Brand metrics`, `C: Advertisement` |
| `QuestionLabel` | Full question text (the dropdown and title) |
| `QuestionType` | `Single`, `Multi` or `Grid`; drives which chart shows |
| `ChartType` | Documentation only |
| `ExposedOnly` / `CompareGroups` | Asked of the exposed group only, or compared across groups |
| `BaseDescription` | Plain-language base, used in the base note |
| `BaseVariesByItem` | True when a grid's base differs by row (B2.a) |

## Items (dimension, 29 rows)

| Column | Description |
|---|---|
| `ItemKey` | `QuestionID|item`, for example `C5|Creative`; `QuestionID|-` for single and multi questions |
| `QuestionID` | Owning question (not related in the model) |
| `ItemLabel` / `ItemOrder` | Row label and order |

## Categories (dimension, 87 rows)

| Column | Description |
|---|---|
| `CategoryKey` | `QuestionID|code`, for example `B4|5`; for multi questions `QuestionID|option` |
| `QuestionID` | Owning question (used by `TREATAS` in the base measures; not related in the model) |
| `CategoryLabel` | Answer label |
| `CategoryOrder` | Position within the question |
| `Colour` | Bar colour (hex) |
| `CategorySort` | One global sort value per label, so `CategoryLabel` can be sorted by it |

## Answers (fact, 25,600 rows)

`RespondentID`, `QuestionID`, `ItemKey`, `CategoryKey`. One row per respondent per question per item per answer chosen.

## Bases (fact, 20,214 rows)

`RespondentID`, `QuestionID`, `ItemKey`. One row per respondent eligible for the question (per grid row for grids).

## Validation (not loaded into the model)

Expected weighted percentage and unweighted base for selected answers, computed with the same logic as the DAX measures.
