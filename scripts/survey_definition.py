"""BrandX survey definition.

This is the only survey-specific file. To rebuild the explorer for another
survey, rewrite this file: load your data, map your subgroup fields, and list
your questions in QUESTIONS. build_model.py does not need to change.
"""
import numpy as np
import pandas as pd
import pyreadstat

SECTIONS = {'A': 'A: Screening', 'B': 'B: Brand metrics', 'C': 'C: Advertisement'}

# Bar colours by scale type (hex). Grid and single questions use one colour per answer.
PALETTES = {
    'pos':   ['#C26A00', '#F2B872', '#D9DEE7', '#7FA6DB', '#0047AB'],
    'agree': ['#0047AB', '#7FA6DB', '#D9DEE7', '#F2B872', '#C26A00'],
    'freq':  ['#0B2E6B', '#0047AB', '#5B8BD0', '#A9C3E8', '#D9DEE7'],
    'nps':   ['#C26A00', '#D9DEE7', '#0047AB'],
    'yn':    ['#0047AB', '#E39A3B', '#D9DEE7'],
}

# Column prefixes stripped to build short item keys (for example B2_BrandX -> B2|BrandX).
ITEM_PREFIXES = r'^(A5_|B2aBand_|B1_Mention_|B2_|C5_)'

BRANDS = [('BrandX', 'BrandX'), ('Lays', "Lay's"), ('Pringles', 'Pringles'), ('Ruffles', 'Ruffles'),
          ('KettleBrand', 'Kettle Brand'), ('Utz', 'Utz'), ('Herrs', "Herr's")]
B1_MENTIONS = [('BrandX', 'BrandX'), ('Lays', "Lay's"), ('Pringles', 'Pringles'), ('Ruffles', 'Ruffles'),
               ('Doritos', 'Doritos'), ('MissVickies', "Miss Vickie's"), ('KettleBrand', 'Kettle Brand'),
               ('Cheetos', 'Cheetos'), ('OldDutch', 'Old Dutch'), ('Tostitos', 'Tostitos'), ('Takis', 'Takis'),
               ('SunChips', 'SunChips'), ('CapeCod', 'Cape Cod'), ('Herrs', "Herr's"), ('Utz', 'Utz'),
               ('StoreBrand', 'Store / private label'), ('PC', "President's Choice"),
               ('None', "None / don't know")]
B3_SHORT = ['Never heard of it', 'Heard of it, know very little', 'Somewhat familiar, never consumed',
            'Familiar, consume occasionally', 'Very familiar, consume regularly']


def load(sav_path):
    """Read the SPSS file and add derived variables. Returns (df, value_labels)."""
    df, meta = pyreadstat.read_sav(sav_path)
    # B2a impression bands per brand: 1-6, 7-8, 9-10 (blank if not aware)
    for key, _ in BRANDS:
        v = df['B2a_' + key]
        df['B2aBand_' + key] = np.where(v.isna(), np.nan, np.where(v >= 9, 3, np.where(v >= 7, 2, 1)))
    return df, meta.variable_value_labels


def respondents(df, vl):
    """One row per respondent: group, weight, and every subgroup field with a sort column."""
    lab = lambda var: df[var].map(vl[var]) if var in vl else df[var]
    return pd.DataFrame({
        'RespondentID': df.RespondentID.astype(int),
        'StudyGroup': df.Study_Group.map({1: 'Exposed', 2: 'Control'}),
        'StudyGroupOrder': df.Study_Group.astype(int),
        'Weight': df['Weight_Final2'].round(6),
        'Gender': lab('A2'), 'Gender_Order': df.A2.astype(int),
        'AgeGroup': lab('Age_Group3').str.replace('–', '-'), 'AgeGroup_Order': df.Age_Group3.astype(int),
        'Region': lab('Region6'), 'Region_Order': df.Region6.astype(int),
        'CommunityType': lab('D9'), 'CommunityType_Order': df.D9.astype(int),
        'ChipUsage': lab('Heavy_Chip_User'), 'ChipUsage_Order': (2 - df.Heavy_Chip_User).astype(int),
        'SnackPurchase': df.SnackFreq2.map({1: 'High frequency', 0: 'Low frequency'}),
        'SnackPurchase_Order': (2 - df.SnackFreq2).astype(int),
        'ShoppingRole': df.Shopping_Role.map({1: 'Primary shopper', 0: 'Non-primary shopper'}),
        'ShoppingRole_Order': (2 - df.Shopping_Role).astype(int),
    })


def exposed_mask(df):
    return (df.Study_Group == 1).values


def questions(vl):
    """Questions shown in the explorer dropdown, in display order.

    Keys:
      id, sec, type ('single' | 'multi' | 'grid'), title, base (text shown under the chart)
      var            single questions: the SPSS variable
      items          multi: [(0/1 dummy column, label)]; grid: [(column, row label)]
      cats           single and grid: [(code, label)] in display order
      scale          palette name from PALETTES (omit for one colour)
      exposed=True   asked of the exposed group only
      basevar=(v,c)  asked only where variable v == code c
      rowbase=True   grid where the base differs by row
    """
    return [
        dict(id='A5', sec='A', type='grid', scale='freq',
             title='A5. During the past month, how frequently have you watched each of the following TV channels? (Select one per line)',
             base='All respondents. Viewing of Channel A or B defines the exposed group; control respondents watched neither',
             items=[('A5_ChannelA', 'Channel A'), ('A5_ChannelB', 'Channel B'), ('A5_ChannelC', 'Channel C'),
                    ('A5_ChannelD', 'Channel D'), ('A5_ChannelE', 'Channel E')],
             cats=[(k, vl['A5_ChannelA'][k]) for k in [1, 2, 3, 4, 5]]),
        dict(id='B1', sec='B', type='multi',
             title='B1. When you think of potato chips, what brands come to mind first? Please list as many as you can think of. (Unaided, coded)',
             base='All respondents; multiple mentions, so answers add to more than 100%',
             items=[('B1_Mention_' + k, l) for k, l in B1_MENTIONS]),
        dict(id='B2', sec='B', type='multi',
             title='B2. Which of the following potato chip brands, if any, have you heard of? (Select all that apply)',
             base='All respondents; multiple answers allowed', items=[('B2_' + k, l) for k, l in BRANDS]),
        dict(id='B2a', sec='B', type='grid', scale='nps', rowbase=True,
             title='B2.a On a scale of 1 to 10, how would you rate your overall impression of each of the following potato chip brands? (1 = Poor, 10 = Excellent)',
             base='Respondents aware of each brand (B2); the base differs by brand',
             items=[('B2aBand_' + k, l) for k, l in BRANDS], cats=[(1, '1-6'), (2, '7-8'), (3, '9-10')]),
        dict(id='B3', sec='B', type='single', scale='pos',
             title='B3. How familiar are you with BrandX potato chips? (Select one)', base='All respondents', var='B3',
             cats=[(k, B3_SHORT[i]) for i, k in enumerate([1, 2, 3, 4, 5])]),
        dict(id='B4', sec='B', type='single', scale='pos',
             title='B4. When you are considering purchasing potato chips, how likely are you to consider BrandX? (Select one)',
             base='All respondents', var='B4', cats=[(k, vl['B4'][k]) for k in [1, 2, 3, 4, 5]]),
        dict(id='B5', sec='B', type='single', scale='nps',
             title='B5. On a scale of 1 to 10, how likely are you to recommend BrandX potato chips to a friend or family member?',
             base='All respondents; NPS = % promoters (9-10) minus % detractors (1-6)', var='Recommendation_Band',
             cats=[(1, 'Detractors (1-6)'), (2, 'Passives (7-8)'), (3, 'Promoters (9-10)')]),
        dict(id='C1', sec='C', type='single', scale='yn', exposed=True,
             title='C1. Have you seen or heard any advertisements for BrandX potato chips recently? (Select one)',
             base='Exposed respondents only', var='C1', cats=[(1, 'Yes'), (2, 'No'), (3, 'Not sure')]),
        dict(id='C2', sec='C', type='single', exposed=True, basevar=('C1', 1),
             title='C2. Where did you see or hear the advertisement? (Select one)',
             base='Exposed respondents who recall BrandX advertising (C1 = Yes)', var='C2',
             cats=[(k, vl['C2'][k].replace(' (please specify)', '')) for k in range(1, 10)]),
        dict(id='C3', sec='C', type='single', scale='yn', exposed=True,
             title='C3. After watching this advertisement, do you recall seeing it before? (Select one)',
             base='Exposed respondents only', var='C3',
             cats=[(1, 'Yes, remember seeing it before'), (2, 'No, do not recall it'), (3, 'Not sure')]),
        dict(id='C4', sec='C', type='single', scale='pos', exposed=True,
             title='C4. On a scale of 1 to 5, how much did you enjoy the advertisement you just watched? (Select one)',
             base='Exposed respondents only', var='C4',
             cats=[(1, '1 - Did not enjoy it at all'), (2, '2'), (3, '3'), (4, '4'), (5, '5 - Enjoyed it a lot')]),
        dict(id='C5', sec='C', type='grid', scale='agree', exposed=True,
             title='C5. Please indicate how much you agree or disagree with the following statements about the advertisement. (Select one per line)',
             base='Exposed respondents only',
             items=[('C5_Creative', 'The advertisement was creative'), ('C5_Memorable', 'The advertisement was memorable'),
                    ('C5_TryBrandX', 'It made me want to try BrandX'), ('C5_Believable', 'The advertisement was believable'),
                    ('C5_Connected', 'The advertisement connected with me'), ('C5_Informative', 'The advertisement was informative')],
             cats=[(k, vl['C5_Creative'][k]) for k in [5, 4, 3, 2, 1]]),
        dict(id='C6', sec='C', type='multi', exposed=True,
             title='C6. In your own words, please describe the main message or key takeaway of the advertisement. (Open-ended, coded into themes)',
             base='Exposed respondents only; a response can carry more than one theme',
             items=[('taste_flavor', 'Great taste and flavour'), ('quality_ingredients', 'High-quality ingredients'),
                    ('crunchy_texture', 'Crunchy, satisfying texture'), ('fun_social', 'Fun, any occasion'),
                    ('healthier_option', 'Healthier snack choice'), ('promotion_limited', 'Limited-time offer'),
                    ('brand_cta', 'Brand mention only'), ('generic_ad', '"A chips ad", no specific message'),
                    ('no_clear_message', 'No clear message / unsure')]),
        dict(id='C7', sec='C', type='single', exposed=True,
             title='C7. Which of the following do you believe was the main message of the advertisement? (Select one)',
             base='Exposed respondents only', var='C7',
             cats=[(k, vl['C7'][k].replace(' (please specify)', '')) for k in [1, 2, 3, 4, 5, 6, 7]]),
    ]


# Checks written to Validation.csv: (QuestionID, CategoryKey, ItemKey, label)
CHECKS = [('B2', 'B2|BrandX', 'B2|-', 'Aided awareness: BrandX'), ('B1', 'B1|BrandX', 'B1|-', 'Unaided recall: BrandX'),
          ('B4', 'B4|4', 'B4|-', 'Consideration: somewhat likely'), ('B4', 'B4|5', 'B4|-', 'Consideration: very likely'),
          ('B5', 'B5|3', 'B5|-', 'Promoters (9-10)'), ('B5', 'B5|1', 'B5|-', 'Detractors (1-6)'),
          ('B2a', 'B2a|3', 'B2a|BrandX', 'BrandX impression 9-10 (among aware)'),
          ('C1', 'C1|1', 'C1|-', 'Recall recent BrandX advertising'), ('C2', 'C2|1', 'C2|-', 'Ad seen on TV (among C1 = Yes)'),
          ('C4', 'C4|5', 'C4|-', 'Enjoyed it a lot (5)'), ('C7', 'C7|1', 'C7|-', 'Main message: great taste')]
