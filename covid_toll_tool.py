#!/usr/bin/env python3

"""
Use OWID's data to create PNG charts and CSV datasets of all-cause mortality compared to COVID-19 mortality, for a given
country and year, in the context of vaccinations count, virus testing, restrictions stringency and the country's
all-cause mortality in preceding years.
"""

__author__ = "Maciej Sieczka <msieczka@sieczka.org>"

import argparse
import sys
import pandas as pd
import matplotlib.pyplot as mpyplot
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from datetime import date as ddate
from datetime import datetime as ddatetime


if sys.version_info < (3, 9):
    print("Python 3.9+ is required to run this script.")
    sys.exit(1)


def main(country, year, if_list_countries, if_interpolate):
    morta_death_cols_bgd = ['deaths_2010_all_ages', 'deaths_2011_all_ages', 'deaths_2012_all_ages',
                            'deaths_2013_all_ages', 'deaths_2014_all_ages', 'deaths_2015_all_ages',
                            'deaths_2016_all_ages', 'deaths_2017_all_ages', 'deaths_2018_all_ages',
                            'deaths_2019_all_ages']

    morta_death_cols_all = morta_death_cols_bgd + ['deaths_2020_all_ages', 'deaths_2021_all_ages',
                                                   'deaths_2022_all_ages']

    morta_cols = ['location', 'date', 'time', 'time_unit'] + morta_death_cols_all

    covid_cols = ['location', 'date', 'new_cases_smoothed', 'new_tests_smoothed', 'new_deaths', 'stringency_index',
                  'people_vaccinated', 'people_fully_vaccinated', 'total_boosters', 'population']

    df_covid = pd.read_csv("./owid-covid-data.csv", parse_dates=['date'], usecols=covid_cols).reindex(
        columns=covid_cols)

    df_morta = pd.read_csv("./excess_mortality.csv", parse_dates=['date'], usecols=morta_cols).reindex(
        columns=morta_cols)

    common_countries = sorted(set(df_morta['location']) & set(df_covid['location']))

    if if_list_countries:
        list_countries(common_countries)

    elif country == 'ALL':
        for country in common_countries:
            orchestrate(country, df_covid, df_morta, year, morta_death_cols_bgd, morta_death_cols_all, if_interpolate)

    elif country in common_countries:
        orchestrate(country, df_covid, df_morta, year, morta_death_cols_bgd, morta_death_cols_all, if_interpolate)

    else:
        print("Country '{}' is not present in both input datasets.\n".format(country))
        list_countries(common_countries)


def list_countries(common_countries):
    print("Please set '--country' to one of the following {} countries present in both input datasets, or 'ALL', to "
          "process them all one by one: {}.".
          format(len(common_countries), ', '.join("'{}'".format(c) for c in common_countries)))


# Charts for the adjacent years (2020, 2021, 2022) overlap by one week, so that e.g. the last week of data on the 2020's
# chart is a copy of the 1st week on the 2021's chart. Effectively, there are 54 weeks of data on a chart of the
# 53-weeks long 2020, and 53 weeks of data on charts of 52 weeks-long 2021 and 2022.
#
# All-cause mortality weekly data series in OWID's excess_mortality.csv for 2010-2019 are all 52 weeks-long. To derive
# and draw 54 weeks of min, max and mean historical 2010-2019 mortality for a 2020 chart, I append each such year's
# death count series with a following year's 1st 2 weeks - e.g. death count 2010's series is appended with the 1st 2
# weeks of 2011, 2011's series with the 1st 2 weeks of 2012 etc. For 2021 and 2022 charts, which are 53 weeks-long, only
# one such week is appended. In case of 2015 (which has 53 weeks, but its death count data series is capped at week 52
# anyway in excess_mortality.csv) death count for the missing 53rd week is interpolated linearly from 2015's 52nd week
# and the 1st week of 2016.
def orchestrate(country, df_covid, df_morta, year, morta_death_cols_bgd, morta_death_cols_all, if_interpolate):

    # Select only the data of a specific country.
    df_covid_country = df_covid[df_covid['location'] == country].copy().reset_index(drop=True)
    df_morta_country = df_morta[df_morta['location'] == country].copy().reset_index(drop=True)

    morta_death_cols_bgd_notnull = [c for c in morta_death_cols_bgd if df_morta_country[c].notnull().any()]
    morta_year_bgd_notnull_min = morta_death_cols_bgd_notnull[0].split('_')[1]
    morta_year_bgd_notnull_max = morta_death_cols_bgd_notnull[-1].split('_')[1]

    if df_morta_country['time_unit'].nunique() == 1:
        time_unit = df_morta_country['time_unit'].unique()[0]

        # Create ISO-week date index, starting at the end (7 = Sunday) of the 1st week of a year, and ending at the end
        # of the 1st week of the following year. So that there's a 1 week overlap between charts for subsequent years -
        # (eg. a 2020 chart will also have the 1st week of 2021). By ISO specification December 28th is always in the
        # last week of the year.
        dates_weekly_one = [ddatetime.fromisocalendar(year=year, week=w, day=7).strftime('%Y-%m-%d')
                            for w in range(1, ddate(year=year, month=12, day=28).isocalendar().week + 1)
                            ] + [ddatetime.fromisocalendar(year=year + 1, week=1, day=7).strftime('%Y-%m-%d')]

        df_dates_weekly_one = pd.DataFrame(dates_weekly_one, columns=['date'], dtype='datetime64[ns]')

        df_morta_country_all, df_morta_country_one = process_morta_df(df_morta_country, df_dates_weekly_one, time_unit,
                                                                      morta_death_cols_all, country)

        df_covid_country_all, df_covid_country_one = process_covid_df(df_covid_country, df_dates_weekly_one, time_unit,
                                                                      if_interpolate)

        df_merge_country_one = merge_covid_morta_dfs(df_covid_country_one, df_morta_country_one, year,
                                                     morta_death_cols_bgd)

        # Find the Y axis bottom and top value in all-time death counts for a given country; to have an identical Y axis
        # range on that country's charts in different years. For some countries the number of non-covid deaths in a
        # given year (e.g. Belgium in 2020) happens to be lower than the lowest number of deaths from all causes in
        # previous years. For some, it's higher than the highest number of deaths in previous years - probably due to
        # borked data, but anyway (e.g. Kyrgyzstan in 2020 - see https://github.com/owid/covid-19-data/issues/1550).
        deaths_noncovid_all = df_morta_country_all.set_index('date')['deaths'].sub(
            df_covid_country_all.set_index('date')['new_deaths'])

        # This conditional is due to `deaths_noncovid_all` being all NaN under certain conditions. E.g. Greenland didn't
        # have any covid deaths until 2021-12-27, and its all-cause mortality ended in Sep 2021, as of
        # excess_mortality.csv at d4dfef79a8.
        if deaths_noncovid_all.isnull().all():
            y_min = df_morta_country_all['deaths'].min()
            y_max = df_morta_country_all['deaths'].max()
        else:
            y_min = min(deaths_noncovid_all.min(), df_morta_country_all['deaths'].min())
            y_max = max(deaths_noncovid_all.max(), df_morta_country_all['deaths'].max())

        plot_weekly(df_merge_country_one, country, year, morta_year_bgd_notnull_min, morta_year_bgd_notnull_max,
                    time_unit, y_min, y_max)


def process_morta_df(df_morta_country, df_dates_weekly_one, time_unit, morta_death_cols_all, country):
    morta_year_all_min = int(morta_death_cols_all[0].split('_')[1])
    morta_year_all_max = int(morta_death_cols_all[-1].split('_')[1])

    # From morta_year_all_min to morta_year_all_max. So that there is data overlap at year boundaries (e.g. for
    # 2015 52 -> 53 weeks interpolation).
    # NOTE: pd.date_range(start=str(morta_year_all_min), end=str(morta_year_all_max+2), freq='W') would be
    # simpler, but we need to start at 1st ISO week, while e.g. pd.date_range(start='2010', end='2021', freq='W')
    # returns '2010-01-03' as the 1st week of 2010, whereas per ISO-week convention (see e.g.
    # pd.date_range(start='2010', end='2011', freq='W')[0].isocalendar()) it's actually the 53rd week of 2009.
    dates_weekly_all = []
    for y in range(morta_year_all_min, morta_year_all_max + 1):
        for w in range(1, ddate(year=y, month=12, day=28).isocalendar().week + 1):
            dates_weekly_all.append(ddatetime.fromisocalendar(year=y, week=w, day=7).strftime('%Y-%m-%d'))

    # Append 1st 4 weeks of the following year, to make sure dates_weekly_all is long enough for
    # df_dates_weekly_one_weeks_count later on.
    for w in range(1, 5):
        dates_weekly_all.append(
            ddatetime.fromisocalendar(year=morta_year_all_max + 1, week=w, day=7).strftime('%Y-%m-%d'))

    if time_unit == 'monthly':
        # From morta_year_all_min to morta_year_all_max. So that there is data overlap at year boundaries for
        # monthly -> weekly interpolation.
        dates_monthly_all = pd.date_range(start=str(morta_year_all_min), end=str(morta_year_all_max + 1), freq='M')

        df_morta_country_all_monthly = pd.DataFrame(dates_monthly_all, columns=['date'], dtype='datetime64[ns]')

        # Merge all morta_death_cols_all into one.
        df_morta_country_all_monthly['deaths'] = pd.concat(
            [df_morta_country[c][0:12] for c in df_morta_country[morta_death_cols_all]],
            axis='rows', ignore_index=True)

        # Up-sample and interpolate monthly mortality data to weekly so that it can be used with other weekly data.
        df_morta_country_all_monthly = df_morta_country_all_monthly.set_index('date').resample(rule='W').first(). \
            interpolate(limit_area='inside').reset_index()

        # Align the up-sampled monthly->weekly all-cause mortality data with the weekly date index which fully
        # encompasses morta_year_all_min up to morta_year_all_max.
        df_dates_weekly_all = pd.DataFrame(dates_weekly_all, columns=['date'], dtype='datetime64[ns]')
        df_morta_country_all = pd.merge(left=df_dates_weekly_all, right=df_morta_country_all_monthly, on='date',
                                        how='left')

    elif time_unit == 'weekly':
        df_morta_country_all = pd.DataFrame(dates_weekly_all, columns=['date'], dtype='datetime64[ns]')

        # Merge all morta_death_cols_all columns into one.
        # NOTE: Eg. pd.concat([df_morta_country[c].dropna() for c in df_morta_country[morta_death_cols_all]],
        # axis='rows', ignore_index=True) would be simpler, but column 'deaths_2015_all_ages' which should have 53
        # records has only 52, so we have to take NaN as ['deaths_2015_all_ages'][52] and interpolate it from its
        # neighbours.
        deaths = []
        for y in range(morta_year_all_min, morta_year_all_max + 1):
            w = ddate(year=y, month=12, day=28).isocalendar().week
            c = 'deaths_{}_all_ages'.format(str(y))
            deaths = deaths + df_morta_country[c][0:w].to_list()

        df_morta_country_all = pd.concat([df_morta_country_all, pd.DataFrame(deaths, columns=['deaths'])],
                                         axis='columns')

        # Interpolate NaNs from nearest neighbours. One such record for sure is 2016-01-03 in all countries' data
        # (53rd week of 2015), but maybe some countries have more. So interpolating it all away, just in case.
        df_morta_country_all['deaths'].interpolate(limit_area='inside', inplace=True)

    # Put df_morta_country back together the way we need it for further processing.
    df_morta_country_one = df_dates_weekly_one.copy()
    df_morta_country_one['location'] = country
    df_morta_country_one['time_unit'] = time_unit
    df_morta_country_one['time'] = df_morta_country_one['date'].dt.isocalendar().week

    df_dates_weekly_one_weeks_count = len(df_dates_weekly_one)
    for y in range(morta_year_all_min, morta_year_all_max + 1):
        col = 'deaths_{}_all_ages'.format(str(y))
        date_start = ddatetime.fromisocalendar(year=y, week=1, day=7).strftime('%Y-%m-%d')
        date_range = pd.date_range(start=date_start, periods=df_dates_weekly_one_weeks_count, freq='W')
        df_morta_country_one[col] = df_morta_country_all[df_morta_country_all['date'].isin(date_range)]['deaths']. \
            to_list()

    return df_morta_country_all, df_morta_country_one


def process_covid_df(df_covid_country, df_dates_weekly_one, time_unit, if_interpolate):

    if if_interpolate:
        # Fill any NaN values with interpolation between the 2 known closest values. Zeros are treated as real data and
        # left intact. Eg. vaccination counts and stringency index data are notoriously missing, Mexico and Ecuador had
        # single missing records of 'new_deaths' at d2e597487d etc.
        df_covid_country['people_vaccinated'].interpolate(limit_area='inside', inplace=True)
        df_covid_country['people_fully_vaccinated'].interpolate(limit_area='inside', inplace=True)
        df_covid_country['total_boosters'].interpolate(limit_area='inside', inplace=True)
        df_covid_country['stringency_index'].interpolate(limit_area='inside', inplace=True)
        df_covid_country['new_cases_smoothed'].interpolate(limit_area='inside', inplace=True)
        df_covid_country['new_tests_smoothed'].interpolate(limit_area='inside', inplace=True)
        df_covid_country['new_deaths'].interpolate(limit_area='inside', inplace=True)

    # NOTE: OWID's positive_rate multiplied by 100 usually equals my positive_test_percent. However, there are
    # countries for which OWID derive positive_rate in a different way than "JHU cases divided by OWID tests". As of
    # writing, this applies to 17 of those 110 countries my script covers at present. For more information see OWID's
    # team replies in https://github.com/owid/covid-19-data/issues/2333.
    #  TODO: Decide whether to use OWID's `positive_rate * 100`, or to stick with `new_cases_smoothed /
    #   new_tests_smoothed * 100`. For now I'll go with the latter, as it allows me to easily spot countries whose cases
    #   or tests count are weird - like Brazil.
    df_covid_country['positive_test_percent'] = \
        df_covid_country['new_cases_smoothed'] / df_covid_country['new_tests_smoothed'] * 100

    df_covid_country['people_vaccinated_percent'] = \
        df_covid_country['people_vaccinated'] / df_covid_country['population'] * 100

    df_covid_country['people_fully_vaccinated_percent'] = \
        df_covid_country['people_fully_vaccinated'] / df_covid_country['population'] * 100

    df_covid_country['total_boosters_percent'] = \
        df_covid_country['total_boosters'] / df_covid_country['population'] * 100

    # Resample the daily covid data to match the weekly mortality data, with week date on Sunday. resample().sum()
    # removes any input non-numeric columns, ie. `location` here, but we don't need it. It also "hides" the `date`
    # column by setting an index on it, but we are going to need this column later on, thus bringing it back with
    # reset_index().
    df_covid_country_all = df_covid_country.resample(rule='W', on='date').agg(
        {'new_deaths': lambda x: x.sum(min_count=1),
         'new_cases_smoothed': lambda x: x.sum(min_count=1),
         'new_tests_smoothed': lambda x: x.sum(min_count=1),
         'positive_test_percent': 'mean',
         'stringency_index': 'mean',
         'people_vaccinated': 'mean',
         'people_fully_vaccinated': 'mean',
         'total_boosters': 'mean',
         'people_vaccinated_percent': 'mean',
         'people_fully_vaccinated_percent': 'mean',
         'total_boosters_percent': 'mean',
         'population': 'mean'}
    ).reset_index()

    if if_interpolate:
        # Interpolate again - now between the weekly values. Due to possible (although very rare) time interval
        # irregularities in the OWID's data, which may cause weekly mean of such non-daily records to be NaN. Eg.
        # Portugal used to have a couple bi-weekly records of 'stringency_index' (see
        # https://github.com/owid/covid-19-data/issues/2258). There was a similar problem with Estonia, Greece and
        # Latvia at that time. I haven't actually observed such issues with data series other than 'stringency index',
        # but let's interpolate them away as well, just in case. This won't do harm - if they don't have NaN records,
        # interpolation will just leave them intact.
        df_covid_country_all['people_vaccinated'].interpolate(limit_area='inside', inplace=True)
        df_covid_country_all['people_fully_vaccinated'].interpolate(limit_area='inside', inplace=True)
        df_covid_country_all['total_boosters'].interpolate(limit_area='inside', inplace=True)
        df_covid_country_all['people_vaccinated_percent'].interpolate(limit_area='inside', inplace=True)
        df_covid_country_all['people_fully_vaccinated_percent'].interpolate(limit_area='inside', inplace=True)
        df_covid_country_all['total_boosters_percent'].interpolate(limit_area='inside', inplace=True)
        df_covid_country_all['stringency_index'].interpolate(limit_area='inside', inplace=True)
        df_covid_country_all['new_cases_smoothed'].interpolate(limit_area='inside', inplace=True)
        df_covid_country_all['new_tests_smoothed'].interpolate(limit_area='inside', inplace=True)
        df_covid_country_all['positive_test_percent'].interpolate(limit_area='inside', inplace=True)
        df_covid_country_all['new_deaths'].interpolate(limit_area='inside', inplace=True)

    # If all-cause mortality data resolution is monthly, we need to adjust daily covid mortality data accordingly.
    # TODO: Come up with something neater than this 'temp' name.
    if time_unit == 'monthly':
        temp = df_covid_country.resample(rule='M', on='date').agg({'new_deaths': lambda x: x.sum(min_count=1)}). \
            resample(rule='W').first(). \
            interpolate(limit_area='inside').reset_index()

        # Align the up-sampled daily->monthly->weekly covid mortality data with the df_covid_country_all's date index,
        # and replace 'new_deaths' there with daily->monthly->weekly data.
        df_covid_country_all['new_deaths'] = pd.merge(
            left=df_covid_country_all[['date']], right=temp, on='date', how='left')['new_deaths']

    # Take only rows of the year specified on command line.
    df_covid_country_one = pd.merge(left=df_dates_weekly_one, right=df_covid_country_all, on='date', how='left')

    return df_covid_country_all, df_covid_country_one


def merge_covid_morta_dfs(df_covid_country_one, df_morta_country, year, morta_death_cols_bgd):
    # Merge both datasets now that they are complete and aligned on same dates.
    df_merge_country_one = pd.merge(df_morta_country, df_covid_country_one, how='inner')

    df_merge_country_one['deaths_min'] = df_merge_country_one[morta_death_cols_bgd].min(axis='columns')
    df_merge_country_one['deaths_max'] = df_merge_country_one[morta_death_cols_bgd].max(axis='columns')
    df_merge_country_one['deaths_mean'] = df_merge_country_one[morta_death_cols_bgd].mean(axis='columns')

    # NOTE: At certain dates, for some countries, one-off upstream corrections in covid mortality counts sometimes
    # happen, leading to over- or under-shoots in deaths_noncovid - https://github.com/owid/covid-19-data/issues/1550.
    df_merge_country_one['deaths_noncovid'] = df_merge_country_one['deaths_{}_all_ages'.format(str(year))].sub(
        df_merge_country_one['new_deaths'], fill_value=None)

    return df_merge_country_one.round(decimals=3)


# TODO: Watch out for the status of 'x_compat'. It's not documented where I'd expect to be [1] although mentioned few
#  times in [2]. If it's going to be depreciated, a workaround will be needed as e.g. per [3], [4].
# [1]https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.plot.html
# [2]https://pandas.pydata.org/pandas-docs/stable/user_guide/visualization.html
# [3]https://stackoverflow.com/questions/12945971/pandas-timeseries-plot-setting-x-axis-major-and-minor-ticks-and-labels
# [4]https://stackoverflow.com/questions/30133280/pandas-bar-plot-changes-date-format
def plot_weekly(df_merge_country_one, country, year, morta_year_bgd_notnull_min, morta_year_bgd_notnull_max, time_unit,
                y_min, y_max):

    fig, axs = mpyplot.subplots(figsize=(13.55, 5.75))  # Create an empty matplotlib figure and axes.

    axs2 = axs.twinx()

    df_merge_country_one.plot(x_compat=True, kind='line', use_index=True, grid=True, rot=50,
                              color=['deepskyblue', 'dimgrey', 'tab:red', 'black', 'black'],
                              style=[':', ':', ':', '-', '--'],
                              ax=axs, x='date', y=['deaths_min', 'deaths_mean', 'deaths_max',
                                                   'deaths_{}_all_ages'.format(str(year)), 'deaths_noncovid'])

    df_merge_country_one.plot(x_compat=True, kind='line', use_index=True, grid=False, rot=50,
                              color=['fuchsia', 'cornflowerblue', 'mediumspringgreen', 'mediumspringgreen',
                                     'mediumspringgreen'],
                              style=['-', '-', '--', '-', '-.'],
                              ax=axs2, x='date', y=['stringency_index', 'positive_test_percent',
                                                    'people_vaccinated_percent', 'people_fully_vaccinated_percent',
                                                    'total_boosters_percent'])

    axs.fill_between(df_merge_country_one['date'], df_merge_country_one['deaths_min'],
                     df_merge_country_one['deaths_max'], alpha=0.25, color='silver')

    axs.legend(['{} lowest death count in {}-{} from all causes'.format(
                    time_unit, morta_year_bgd_notnull_min, morta_year_bgd_notnull_max),
                '{} average death count in {}-{} from all causes'.format(
                    time_unit, morta_year_bgd_notnull_min, morta_year_bgd_notnull_max),
                '{} highest death count in {}-{} from all causes'.format(
                    time_unit, morta_year_bgd_notnull_min, morta_year_bgd_notnull_max),
                '{} death count in {} from all causes'.format(
                    time_unit, year),
                '{} death count in {} from all causes EXCLUDING deaths attributed to COVID-19'.format(
                    time_unit, year),
                'range between highest and lowest {} death count from all causes in {}-{}'.format(
                    time_unit, morta_year_bgd_notnull_min, morta_year_bgd_notnull_max)],
               title='left Y axis:', fontsize='small', handlelength=1.6, loc='upper left',
               bbox_to_anchor=(-0.0845, 1.3752))

    axs2.legend(['restrictions stringency: 0 ~ none, 100 ~ full lockdown',
                 'percent of positive results, aka "cases", in all COVID-19 tests conducted that week',
                 'percent of the country\'s populace who received at least 1 vaccine dose',
                 'percent of the country\'s populace who received all doses according to vaccination protocol',
                 'total booster doses administered, counted as the country\'s populace percentage'],
                title='right Y axis:', fontsize='small', handlelength=1.6, loc='upper right',
                bbox_to_anchor=(1.057, 1.375))

    axs.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1, byweekday=6))

    axs.set_xlabel(xlabel="date (ISO week Sunday)", loc="right")

    axs2.set(ylabel="percent",
             xlim=[df_merge_country_one['date'].head(1), df_merge_country_one['date'].tail(1)],
             ylim=[-0.25, 100.5])

    axs2.yaxis.set_major_locator(mticker.MultipleLocator(10))

    axs.set(ylabel="count",
            xlim=[df_merge_country_one['date'].head(1), df_merge_country_one['date'].tail(1)],
            ylim=[y_min - (abs(y_max) - abs(y_min)) * 0.05, y_max + (abs(y_max) - abs(y_min)) * 0.05])

    axs2.set_xlabel(xlabel="date (ISO week Sunday)", loc="right")

    # Put the axs2 (the right Y axis) below the legend boxes. By default it would overlap the axs'es (left) legend box.
    # See https://github.com/matplotlib/matplotlib/issues/3706.
    legend = axs.get_legend()
    axs.get_legend().remove()
    axs2.add_artist(legend)

    axs.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

    mpyplot.title("{}, {}".format(country, year), fontweight="bold", loc='right')

    mpyplot.figtext(0.065, 0,
                    "This chart was downloaded from https://github.com/czka/covid_toll_tool.\n"
                    "Chart's data source is OWID (Our World in Data), https://github.com/owid/covid-19-data.\n"
                    "For more information about the data presented on this chart please see "
                    "https://github.com/czka/covid_toll_tool/blob/main/README.md.",
                    fontsize=9, va="bottom", ha="left", linespacing=1.5, fontstyle='italic')

    # mpyplot.tight_layout(pad=1)

    fig.savefig('{}_{}.png'.format(country.replace(' ', '_'), year), bbox_inches="tight", pad_inches=0.05,
                pil_kwargs={'optimize': True})

    df_merge_country_one.to_csv('{}_{}.csv'.format(country.replace(' ', '_'), year), index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        add_help=False,
        description=__doc__,
        epilog="The output are a PNG chart and CSV dataset for the '--country' and the '--year' specified on the "
               "command line - e.g. 'Poland_2020.png' and 'Poland_2020.csv'.")

    parser._optionals.title = 'Arguments'

    mutually_exclusive = parser.add_mutually_exclusive_group(required=True)

    mutually_exclusive.add_argument('--list_countries',
                                    action='store_true',
                                    dest='if_list_countries',
                                    help='List countries available in both input CSV files.')

    mutually_exclusive.add_argument('--country',
                                    help="Country to process - e.g. 'Poland'. Use 'ALL' to process all countries one by"
                                         " one.")

    parser.add_argument('--year',
                        required='--country' in sys.argv,
                        type=int,
                        help="Year to process - e.g. '2020'.")

    parser.add_argument('--interpolate',
                        action='store_true',
                        dest='if_interpolate',
                        default=False,
                        help='Interpolate data gaps present in the columns the script reads from the input '
                             'owid-covid-data.csv, linearly from the missing data\'s nearest neighbours. For the sake '
                             'of a more complete chart, but at a cost of a less accurate representation of some of the '
                             'input data. By default interpolation is disabled.')

    parser.add_argument('--help', '-h',
                        action='help',
                        help='Show this help message.')

    args = parser.parse_args()

    main(args.country, args.year, args.if_list_countries, args.if_interpolate)
