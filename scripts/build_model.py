"""Build the six-table Power BI model for the survey explorer.

Usage:
    python scripts/build_model.py data/source/BrandX_Aug2026.sav data/model

Reads the survey through survey_definition.py and writes:
    Respondents.csv  Questions.csv  Items.csv  Categories.csv
    Answers.csv      Bases.csv      Validation.csv

This file is survey-agnostic. To reuse it, change survey_definition.py only.
"""
import heapq
import os
import re
import sys

import numpy as np
import pandas as pd

import survey_definition as S

CHART = {'single': 'Bar', 'multi': 'Bar (sorted)', 'grid': '100% stacked bar'}


def short(col):
    return re.sub(S.ITEM_PREFIXES, '', col)


def build(df, vl):
    R = S.respondents(df, vl)
    Q = S.questions(vl)
    E = S.exposed_mask(df)
    ids = df.RespondentID.astype(int)
    qrows, irows, crows, ans, base = [], [], [], [], []

    for qi, q in enumerate(Q, 1):
        qid, typ = q['id'], q['type']
        # Eligibility: who was asked this question. This becomes the Bases table.
        elig = np.ones(len(df), bool)
        if q.get('exposed'):
            elig &= E
        if 'basevar' in q:
            elig &= (df[q['basevar'][0]] == q['basevar'][1]).values
        qrows.append({'QuestionID': qid, 'QuestionOrder': qi, 'Section': S.SECTIONS[q['sec']],
                      'QuestionLabel': q['title'], 'QuestionType': typ.capitalize(), 'ChartType': CHART[typ],
                      'ExposedOnly': bool(q.get('exposed')), 'CompareGroups': not q.get('exposed'),
                      'BaseDescription': q['base'], 'BaseVariesByItem': bool(q.get('rowbase'))})
        pal = S.PALETTES.get(q.get('scale'))

        if typ == 'multi':
            # One placeholder item; each selected option is an answer row.
            irows.append({'ItemKey': f'{qid}|-', 'QuestionID': qid, 'ItemLabel': '(none)', 'ItemOrder': 0})
            for ci, (col, label) in enumerate(q['items'], 1):
                ck = f'{qid}|{short(col)}'
                crows.append({'CategoryKey': ck, 'QuestionID': qid, 'CategoryLabel': label,
                              'CategoryOrder': ci, 'Colour': '#0047AB'})
                sel = elig & (df[col] == 1).values
                ans.append(pd.DataFrame({'RespondentID': ids[sel], 'QuestionID': qid,
                                         'ItemKey': f'{qid}|-', 'CategoryKey': ck}))
            answered = elig & df[q['items'][0][0]].notna().values
            base.append(pd.DataFrame({'RespondentID': ids[answered], 'QuestionID': qid, 'ItemKey': f'{qid}|-'}))

        elif typ == 'single':
            irows.append({'ItemKey': f'{qid}|-', 'QuestionID': qid, 'ItemLabel': '(none)', 'ItemOrder': 0})
            codes = {}
            for ci, (code, label) in enumerate(q['cats'], 1):
                ck = f'{qid}|{int(code)}'
                codes[code] = ck
                crows.append({'CategoryKey': ck, 'QuestionID': qid, 'CategoryLabel': label,
                              'CategoryOrder': ci, 'Colour': pal[ci - 1] if pal else '#0047AB'})
            v = df[q['var']]
            m = elig & v.isin(list(codes)).values
            ans.append(pd.DataFrame({'RespondentID': ids[m], 'QuestionID': qid,
                                     'ItemKey': f'{qid}|-', 'CategoryKey': v[m].map(codes)}))
            base.append(pd.DataFrame({'RespondentID': ids[m], 'QuestionID': qid, 'ItemKey': f'{qid}|-'}))

        else:  # grid: one item per row, base per row
            codes = {}
            for ci, (code, label) in enumerate(q['cats'], 1):
                ck = f'{qid}|{int(code)}'
                codes[code] = ck
                crows.append({'CategoryKey': ck, 'QuestionID': qid, 'CategoryLabel': label,
                              'CategoryOrder': ci, 'Colour': pal[ci - 1]})
            for ii, (col, label) in enumerate(q['items'], 1):
                ik = f'{qid}|{short(col)}'
                irows.append({'ItemKey': ik, 'QuestionID': qid, 'ItemLabel': label, 'ItemOrder': ii})
                v = df[col]
                m = elig & v.isin(list(codes)).values
                ans.append(pd.DataFrame({'RespondentID': ids[m], 'QuestionID': qid,
                                         'ItemKey': ik, 'CategoryKey': v[m].map(codes)}))
                base.append(pd.DataFrame({'RespondentID': ids[m], 'QuestionID': qid, 'ItemKey': ik}))

    Qdf, Idf, Cdf = pd.DataFrame(qrows), pd.DataFrame(irows), pd.DataFrame(crows)
    A = pd.concat(ans, ignore_index=True)
    B = pd.concat(base, ignore_index=True)
    Cdf['CategorySort'] = category_sort(Qdf, Cdf)
    return R, Qdf, Idf, Cdf, A, B


def category_sort(Qdf, Cdf):
    """One sort value per CategoryLabel.

    Power BI's Sort by column needs exactly one sort value per label, but the same
    label (for example "Not sure") appears in several questions. This builds a
    topological order of the within-question sequences; earlier questions win
    any conflict.
    """
    qo = dict(zip(Qdf.QuestionID, Qdf.QuestionOrder))
    Cs = Cdf.assign(QO=Cdf.QuestionID.map(qo)).sort_values(['QO', 'CategoryOrder'])
    succ = {l: set() for l in Cs.CategoryLabel}
    indeg = {l: 0 for l in succ}

    def reach(a, b):
        st, seen = [a], set()
        while st:
            x = st.pop()
            if x == b:
                return True
            if x in seen:
                continue
            seen.add(x)
            st.extend(succ[x])
        return False

    for _, g in Cs.groupby('QO', sort=True):
        labs = list(g.CategoryLabel)
        for a, b in zip(labs, labs[1:]):
            if b not in succ[a] and not reach(b, a):
                succ[a].add(b)
                indeg[b] += 1
    first = {}
    for i, l in enumerate(Cs.CategoryLabel):
        first.setdefault(l, i)
    h = [(first[l], l) for l in succ if indeg[l] == 0]
    heapq.heapify(h)
    rank = {}
    while h:
        _, l = heapq.heappop(h)
        rank[l] = len(rank) + 1
        for b in succ[l]:
            indeg[b] -= 1
            if indeg[b] == 0:
                heapq.heappush(h, (first[b], b))
    return Cdf.CategoryLabel.map(rank).astype(int)


def validation(R, A, B):
    """Expected results computed exactly as the DAX measures compute them."""
    M = A.merge(R[['RespondentID', 'StudyGroup', 'Weight']], on='RespondentID')
    Bm = B.merge(R[['RespondentID', 'StudyGroup', 'Weight']], on='RespondentID')
    rows = []
    for qid, ck, ik, label in S.CHECKS:
        for g in ['Exposed', 'Control']:
            den = Bm[(Bm.QuestionID == qid) & (Bm.ItemKey == ik) & (Bm.StudyGroup == g)]
            if len(den) == 0:
                continue
            num = M[(M.CategoryKey == ck) & (M.ItemKey == ik) & (M.StudyGroup == g)].Weight.sum()
            rows.append({'Check': label, 'QuestionID': qid, 'CategoryKey': ck, 'ItemKey': ik, 'StudyGroup': g,
                         'ExpectedWeightedPct': round(num / den.Weight.sum(), 4),
                         'ExpectedUnweightedBase': len(den)})
    return pd.DataFrame(rows)


def main(sav_path, out_dir):
    df, vl = S.load(sav_path)
    R, Qdf, Idf, Cdf, A, B = build(df, vl)
    V = validation(R, A, B)
    os.makedirs(out_dir, exist_ok=True)
    for name, t in [('Respondents', R), ('Questions', Qdf), ('Items', Idf), ('Categories', Cdf),
                    ('Answers', A), ('Bases', B), ('Validation', V)]:
        t.to_csv(os.path.join(out_dir, f'{name}.csv'), index=False, encoding='utf-8')
        print(f'{name:12s} {len(t):>7,} rows')
    print(V.to_string(index=False))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
