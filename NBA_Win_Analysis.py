#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 16 15:37:41 2026

@author: ajross
"""


'''
NBA Team Stats vs Winning — 2010-11 through 2025-26
Which box score stats actually correlate with winning?
'''

import time
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from adjustText import adjust_text
from nba_api.stats.endpoints import leaguedashteamstats

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 250)

OUTPUT_DIR = '/Users/ajross/Desktop/SportsProj'
SEASONS = [f"{y}-{str(y + 1)[-2:]}" for y in range(2010, 2026)]

# Columns pulled from the 'Base' endpoint (team's own stats)
OWN_COLS = ['TEAM_NAME', 'PTS', 'AST', 'OREB', 'DREB', 'REB', 'STL', 'BLK', 'BLKA',
            'TOV', 'FG_PCT', 'FG3_PCT', 'FT_PCT', 'FTM', 'FTA', 'FGM', 'FGA',
            'FG3M', 'FG3A', 'W_PCT', 'W', 'L']

# Columns pulled from the 'Opponent' endpoint
OPP_COLS = ['TEAM_NAME', 'OPP_PTS', 'OPP_TOV', 'OPP_FTA', 'OPP_FG_PCT', 'OPP_OREB']

# Rank direction: which way is good for each stat
HIGHER_BETTER = ['PTS', 'AST', 'OREB', 'DREB', 'REB', 'STL', 'BLK', 'FG_PCT',
                 'FG3_PCT', 'FT_PCT', 'FTM', 'FTA', 'FGM', 'FGA', 'FG3M', 'FG3A',
                 'W_PCT', 'OPP_TOV']
LOWER_BETTER = ['TOV', 'BLKA', 'OPP_PTS', 'OPP_FTA', 'OPP_FG_PCT', 'OPP_OREB']

RANK_COLS = [f'{c}_RANK' for c in HIGHER_BETTER + LOWER_BETTER]

CHAMPIONS = {
    '2010-11': 'Dallas Mavericks',
    '2011-12': 'Miami Heat',
    '2012-13': 'Miami Heat',
    '2013-14': 'San Antonio Spurs',
    '2014-15': 'Golden State Warriors',
    '2015-16': 'Cleveland Cavaliers',
    '2016-17': 'Golden State Warriors',
    '2017-18': 'Golden State Warriors',
    '2018-19': 'Toronto Raptors',
    '2019-20': 'Los Angeles Lakers',
    '2020-21': 'Milwaukee Bucks',
    '2021-22': 'Golden State Warriors',
    '2022-23': 'Denver Nuggets',
    '2023-24': 'Boston Celtics',
    '2024-25': 'Oklahoma City Thunder',
    '2025-26': 'New York Knicks',
}


# =============================================================================
# HELPERS
# =============================================================================

def pull_season(season):
 # Pull one season of team stats and return a 30-row DataFrame with ranks 
    own = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        measure_type_detailed_defense='Base',
        per_mode_detailed='PerGame'
    ).get_data_frames()[0][OWN_COLS]

    opp = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        measure_type_detailed_defense='Opponent',
        per_mode_detailed='PerGame'
    ).get_data_frames()[0][OPP_COLS]

    df = own.merge(opp, on='TEAM_NAME')
    df['WIN_PCT'] = df['W'] / (df['W'] + df['L'])

    for col in HIGHER_BETTER:
        df[f'{col}_RANK'] = df[col].rank(ascending=False).astype(int)
    for col in LOWER_BETTER:
        df[f'{col}_RANK'] = df[col].rank(ascending=True).astype(int)

    df['SEASON'] = season
    return df


def save_table(df, filename):
 # Write a DataFrame to a readable .txt in OUTPUT_DIR 
    path = f'{OUTPUT_DIR}/{filename}'
    with open(path, 'w') as f:
        f.write(df.to_string())
    print(f'Saved -> {path}')


# =============================================================================
# PULL ALL DATA 
# =============================================================================

all_seasons = []
for season in SEASONS:
    print(f'Pulling {season}...')
    all_seasons.append(pull_season(season))
    time.sleep(0.6)  # avoid rate-limiting

data = pd.concat(all_seasons, ignore_index=True)
print(f'\nPulled {len(data)} team-seasons.')





# =============================================================================
# SECTION 1 — SINGLE TEAM PROFILE (change team & season below)
# =============================================================================

def team_profile(team_name, season):
 # Print one team's league rank in every stat for a given season 
    row = data[(data['TEAM_NAME'] == team_name) & (data['SEASON'] == season)]
    if row.empty:
        print(f'No data for {team_name} in {season}')
        return None
    ranks = row[RANK_COLS].T
    ranks.columns = ['RANK']
    return ranks.sort_values('RANK')


print('\n=== Single team profile ===')
print(team_profile('Golden State Warriors', '2021-22'))





# =============================================================================
# SECTION 2 — SCATTER PLOT (change x_stat to plot a different stat)
# =============================================================================

def scatter_vs_winpct(season, x_stat, x_label):
    '''Scatter one stat against win % for all 30 teams in a season.''' 
    season_data = data[data['SEASON'] == season]

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.scatter(season_data[x_stat], season_data['WIN_PCT'], s=60, alpha=0.7)

    texts = [
        ax.text(row[x_stat], row['WIN_PCT'], row['TEAM_NAME'], fontsize=7)
        for _, row in season_data.iterrows()
    ]
    adjust_text(texts, arrowprops=dict(arrowstyle='-', color='gray', lw=0.5))

    ax.set_xlabel(x_label)
    ax.set_ylabel('Win %')
    ax.set_title(f'{x_label} vs Win % ({season})')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


scatter_vs_winpct('2025-26', 'OPP_PTS', 'Opponent Points Per Game')
scatter_vs_winpct('2025-26', 'PTS', 'Points Per Game')
scatter_vs_winpct('2020-21', 'BLKA', 'Assists Per Game')




# =============================================================================
# SECTION 3 — CORRELATION WITH WIN % (season by season)
# =============================================================================

stat_cols = [c for c in HIGHER_BETTER + LOWER_BETTER if c != 'W_PCT']

corr_by_season = {}
for season in SEASONS:
    season_data = data[data['SEASON'] == season]
    corr_by_season[season] = season_data[stat_cols + ['WIN_PCT']].corr()['WIN_PCT']

corr_table = pd.DataFrame(corr_by_season).T.drop(columns=['WIN_PCT'])
print('\n=== Correlation with WIN_PCT by season ===')
print(corr_table)
save_table(corr_table, 'correlations.txt')





# =============================================================================
# SECTION 4 — MULTIPLE REGRESSION (season by season)
# =============================================================================

PREDICTORS = ['PTS', 'OPP_PTS', 'OPP_TOV', 'AST', 'DREB', 'OREB', 'BLK', 'BLKA',
              'TOV', 'FG_PCT', 'FG3_PCT', 'FT_PCT']

reg_by_season = {}
for season in SEASONS:
    season_data = data[data['SEASON'] == season]
    X = sm.add_constant(season_data[PREDICTORS])
    y = season_data['WIN_PCT']
    model = sm.OLS(y, X).fit()
    reg_by_season[season] = pd.Series(
        {'R_SQUARED': model.rsquared, **model.params.drop('const')}
    )

regression_table = pd.DataFrame(reg_by_season).T
print('\n=== Regression: R-squared and coefficients by season ===')
print(regression_table)
save_table(regression_table, 'regression.txt')





# =============================================================================
# SECTION 5 — CHAMPION PROFILES
# =============================================================================

champ_mask = data.apply(
    lambda row: row['TEAM_NAME'] == CHAMPIONS.get(row['SEASON']), axis=1
)
champions_df = data[champ_mask][['SEASON', 'TEAM_NAME'] + RANK_COLS]
 
print('\n=== League rank of each champion, by stat ===')
print(champions_df)
save_table(champions_df, 'champions.txt')





# =============================================================================
# SECTION 6 — "CHAMPIONSHIP PROFILE" FILTER
# =============================================================================

mask = (
    (data['PTS_RANK'] <= 15) &
    (data['FG_PCT_RANK'] <= 12) &
    ((data['FG3_PCT_RANK'] <= 12) | (data['FG_PCT_RANK'] <= 1)) &
    ((data['OPP_PTS_RANK'] <= 10) | ((data['PTS_RANK'] <= 1) & (data['FGM_RANK'] <= 1))) &
    (data['W_PCT_RANK'] <= 7) &
    (data['BLKA_RANK'] <= 15) &
    ((data['AST_RANK'] <= 15) | (data['STL_RANK'] <= 3)) &
    (data['FTA_RANK'] >= 8) &
    ((data['FG3M_RANK'] <= 10) | (data['FTA_RANK'] <= 10) |
     ((data['FG_PCT_RANK'] <= 2) & (data['AST_RANK'] <= 2)))
)

matches = data[mask][['SEASON', 'TEAM_NAME'] + RANK_COLS]
print('\n=== Teams matching the championship-profile filter ===')
print(matches)

save_table(matches, 'filter_matches.txt')





# Correclation Check: 

print(data[['PTS', 'OPP_PTS', 'FG_PCT', 'OPP_FG_PCT']].corr())
















