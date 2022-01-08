#!/usr/bin/env python3

"""
Use OWID's data to create PNG charts and CSV datasets of all-cause mortality compared to COVID-19 mortality, for a given
country and year, in the context of vaccinations count, virus testing, lockdown stringency and the country's all-cause
mortality in preceding years.
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


def main(country, year, if_list_countries, if_interpolate_week_53):
    morta_death_cols_bgd = ['deaths_2010_all_ages', 'deaths_2011_all_ages', 'deaths_2012_all_ages',
                            'deaths_2013_all_ages', 'deaths_2014_all_ages', 'deaths_2015_all_ages',
                            'deaths_2016_all_ages', 'deaths_2017_all_ages', 'deaths_2018_all_ages',
                            'deaths_2019_all_ages']

    morta_death_cols_all = morta_death_cols_bgd + ['deaths_2020_all_ages', 'deaths_2021_all_ages']

    morta_cols = ['location', 'date', 'time', 'time_unit'] + morta_death_cols_all

    covid_cols = ['location', 'date', 'new_cases_smoothed', 'new_tests_smoothed', 'new_deaths', 'stringency_index',
                  'people_vaccinated', 'people_fully_vaccinated', 'population']

    df_covid = pd.read_csv("./owid-covid-data.csv", parse_dates=['date'], usecols=covid_cols).reindex(
        columns=covid_cols)

    df_morta = pd.read_csv("./excess_mortality.csv", parse_dates=['date'], usecols=morta_cols).reindex(
        columns=morta_cols)

    common_countries = sorted(set(df_morta['location']) & set(df_covid['location']))

    if if_list_countries:
        list_countries(common_countries)

    elif country == 'ALL':
        for country in common_countries:
            get_it_together(country, df_covid, df_morta, year, if_interpolate_week_53, morta_death_cols_bgd,
                            morta_death_cols_all)

    elif country in common_countries:
        get_it_together(country, df_covid, df_morta, year, if_interpolate_week_53, morta_death_cols_bgd,
                        morta_death_cols_all)

    else:
        print("Country '{}' is not present in both input datasets.\n".format(country))
        list_countries(common_countries)


def list_countries(common_countries):
    print("Please set '--country' to one of the following {} countries present in both input datasets, or 'ALL', to "
          "process them all one by one: {}.".
          format(len(common_countries), ', '.join("'{}'".format(c) for c in common_countries)))


# Charts for the adjacent years (2020, 2021, 2022) overlap by one week, so that e.g. the last week of data on
# the 2020's chart are a copy of the 1st week on the 2021's chart. Effectively, there are 54 weeks of data on
# a chart of the 53-weeks long 2020, and 53 weeks of data on charts of 52 weeks-long 2021 and 2022.
#
# All-cause mortality weekly data series in OWID's excess_mortality.csv for 2010-2019 are all 52 weeks-long. To
# be able to derive and draw 54 weeks of min, max and mean historical 2010-2019 mortality for a 2020 chart, I
# append each such year's death count series with a following year's 1st 2 weeks - e.g. death count 2010's
# series is appended with the 1st 2 weeks of 2011, 2011's series with the 1st 2 weeks of 2012 etc. For 2021 and
# 2022 charts, which are 53 weeks-long, only one such week is appended. In case of 2015 (which has 53 weeks, but
# its death count data series is capped at week 52 anyway in excess_mortality.csv) death count for the missing
# 53rd week is interpolated linearly from 2015's 52nd week and the 1st week of 2016.

def get_it_together(country, df_covid, df_morta, year, if_interpolate_week_53, morta_death_cols_bgd,
                    morta_death_cols_all):

    # Select only the data of a specific country.
    df_covid_country = df_covid[df_covid['location'] == country].copy().reset_index(drop=True)
    df_morta_country = df_morta[df_morta['location'] == country].copy().reset_index(drop=True)

    morta_year_all_min = int(morta_death_cols_all[0].split('_')[1])
    morta_year_all_max = int(morta_death_cols_all[-1].split('_')[1])

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

        df_dates_weekly_one = pd.DataFrame(dates_weekly_one, columns=['date'], dtype='datetime64[ns]')

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
            df_morta_country_all_monthly = df_morta_country_all_monthly.set_index('date').resample(rule='W').first().\
                interpolate(limit_area='inside').reset_index()

            # Align the up-sampled weekly data with the weekly date index which fully encompasses morta_year_all_min up
            # to morta_year_all_max.
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

            # Interpolate NaNs from nearest neighbours. One such record for sure is 2016-01-03 in all countries data
            # (53rd week of 2015), but maybe some countries have more. So interpolating it all away, just in case.
            df_morta_country_all['deaths'].interpolate(limit_area='inside', inplace=True)

        # Put df_morta_country back together the way we need it for further processing.
        df_morta_country = df_dates_weekly_one.copy()
        df_morta_country['location'] = country
        df_morta_country['time_unit'] = time_unit
        df_morta_country['time'] = df_morta_country['date'].dt.isocalendar().week

        df_dates_weekly_one_weeks_count = len(df_dates_weekly_one)
        for y in range(morta_year_all_min, morta_year_all_max + 1):
            col = 'deaths_{}_all_ages'.format(str(y))
            date_start = ddatetime.fromisocalendar(year=y, week=1, day=7).strftime('%Y-%m-%d')
            date_range = pd.date_range(start=date_start, periods=df_dates_weekly_one_weeks_count, freq='W')
            df_morta_country[col] = df_morta_country_all[df_morta_country_all['date'].isin(date_range)]['deaths'].\
                to_list()

        df_merged_one = process_weekly(df_covid_country, df_morta_country, df_dates_weekly_one, year,
                                       morta_death_cols_bgd, if_interpolate_week_53, time_unit)

        # Find the Y axis bottom and top value in all-time death counts for a given country; to have an identical Y axis
        # range on that country's charts in different years.
        # TODO: deaths_noncovid can be lower than any lowest mortality. Include it.
        y_min = df_morta_country_all['deaths'].min()
        y_max = df_morta_country_all['deaths'].max()

        plot_weekly(df_merged_one, country, year, morta_year_bgd_notnull_min, morta_year_bgd_notnull_max, y_min, y_max)


def process_weekly(df_covid_country, df_morta_country, df_weekly_index, year, morta_death_cols_bgd,
                   if_interpolate_week_53, time_unit):
    # For some reason the vaccinated counts are missing for a number of dates. Filling them in with a linear
    # interpolation between the 2 known closest values.
    df_covid_country['people_vaccinated'].interpolate(limit_area='inside', inplace=True)
    df_covid_country['people_fully_vaccinated'].interpolate(limit_area='inside', inplace=True)

    # Gaps happen in lockdown stringency data, too. OWID only take them from the OxCGRT project as they are (see eg.
    # https://github.com/owid/covid-19-data/issues/1961#issuecomment-918357447).
    df_covid_country['stringency_index'].interpolate(limit_area='inside', inplace=True)

    # Resample the daily covid data to match the weekly mortality data, with week date on Sunday.
    # resample().sum() removes any input non-numeric columns, ie. `location` here, but we don't need it. It also "hides"
    # the `date` column by setting an index on it, but we are going to need this column later on, thus bringing it back
    # with reset_index().

    # TODO: Come up with something neater than this 'temp' dataframe.
    if time_unit == 'monthly':
        temp = df_covid_country.resample(rule='M', on='date').agg({'new_deaths': 'sum'}).\
            resample(rule='W').first().\
            interpolate(limit_area='inside').reset_index()

    df_covid_country = df_covid_country.resample(rule='W', on='date').agg(
        {'new_deaths': 'sum',
         'new_cases_smoothed': 'mean',
         'new_tests_smoothed': 'mean',
         'stringency_index': 'mean',
         'people_vaccinated': 'mean',
         'people_fully_vaccinated': 'mean',
         'population': 'mean'}
    ).reset_index()

    if time_unit == 'monthly':
        df_covid_country['new_deaths'] = temp['new_deaths']

    df_covid_country['positive_test_percent'] = \
        df_covid_country['new_cases_smoothed'] / df_covid_country['new_tests_smoothed'] * 100

    df_covid_country['people_vaccinated_percent'] = \
        df_covid_country['people_vaccinated'] / df_covid_country['population'] * 100

    df_covid_country['people_fully_vaccinated_percent'] = \
        df_covid_country['people_fully_vaccinated'] / df_covid_country['population'] * 100

    # Take only rows of the given year.
    df_covid_country = pd.merge(left=df_weekly_index, right=df_covid_country, on='date', how='left')

    # Merge death count during covid *demics in a given year into the covid DataFrame.
    df_covid_country = pd.merge(left=df_covid_country, right=df_morta_country, on='date', how='left')

    # Merge both datasets now that they are aligned on their dates.
    df_merged_one = pd.merge(df_morta_country, df_covid_country, how='inner')

    # TODO: axis=1 -> axis='columns'?
    df_merged_one['deaths_min'] = df_merged_one[morta_death_cols_bgd].min(axis=1)
    df_merged_one['deaths_max'] = df_merged_one[morta_death_cols_bgd].max(axis=1)
    df_merged_one['deaths_mean'] = df_merged_one[morta_death_cols_bgd].mean(axis=1)

    # By ISO specification the 28th of December is always in the last week of the year.
    weeks_count = ddate(year, 12, 28).isocalendar().week

    # TODO: if_interpolate_week_53 is no longer needed.
    if if_interpolate_week_53 and weeks_count == 53:
        df_merged_one.loc[52, 'deaths_min'] = (df_merged_one['deaths_min'][0] + df_merged_one['deaths_min'][51]) / 2
        df_merged_one.loc[52, 'deaths_max'] = (df_merged_one['deaths_max'][0] + df_merged_one['deaths_max'][51]) / 2
        df_merged_one.loc[52, 'deaths_mean'] = (df_merged_one['deaths_mean'][0] + df_merged_one['deaths_mean'][51]) / 2

    df_merged_one['deaths_noncovid'] = df_merged_one['deaths_{}_all_ages'.format(str(year))].sub(
        df_merged_one['new_deaths'], fill_value=None)

    return df_merged_one


def plot_weekly(df_merged_one, country, year, morta_year_bgd_notnull_min, morta_year_bgd_notnull_max, y_min, y_max):

    fig, axs = mpyplot.subplots(figsize=(13.55, 5.75))  # Create an empty matplotlib figure and axes.

    axs2 = axs.twinx()

    # TODO: include monthly/weekly in death count legend.
    df_merged_one.plot(x_compat=True, kind='line', use_index=True, grid=True, rot='50',
                       color=['royalblue', 'grey', 'red', 'black', 'black'], style=[':', ':', ':', '-', '--'],
                       ax=axs, x='date', y=['deaths_min', 'deaths_mean', 'deaths_max',
                                            'deaths_{}_all_ages'.format(str(year)), 'deaths_noncovid'])

    df_merged_one.plot(x_compat=True, kind='line', use_index=True, grid=False, rot='50',
                       color=['fuchsia', 'mediumslateblue', 'mediumspringgreen', 'mediumspringgreen'],
                       style=['-', '-', '--', '-'],
                       ax=axs2, x='date', y=['stringency_index', 'positive_test_percent', 'people_vaccinated_percent',
                                             'people_fully_vaccinated_percent'])

    # TODO: Watch out for the status of 'x_compat' above. It's not documented where it should have been [1] although
    #  mentioned few times in [2]. If it's going to be depreciated, a workaround will be needed as e.g. per [3], [4].
    #  [1] https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.plot.html
    #  [2] https://pandas.pydata.org/pandas-docs/stable/user_guide/visualization.html
    #  [3] https://stackoverflow.com/questions/12945971/pandas-timeseries-plot-setting-x-axis-major-and-minor-ticks-and-labels
    #  [4] https://stackoverflow.com/questions/30133280/pandas-bar-plot-changes-date-format

    axs.fill_between(df_merged_one['date'], df_merged_one['deaths_min'], df_merged_one['deaths_max'], alpha=0.25,
                     color='yellowgreen')

    axs.legend(['lowest death count in {}-{} from all causes'.format(morta_year_bgd_notnull_min, morta_year_bgd_notnull_max),
                'average death count in {}-{} from all causes'.format(morta_year_bgd_notnull_min, morta_year_bgd_notnull_max),
                'highest death count in {}-{} from all causes'.format(morta_year_bgd_notnull_min, morta_year_bgd_notnull_max),
                'death count in {} from all causes'.format(year),
                'death count in {} from all causes MINUS the number of deaths attributed to COVID-19'.format(year),
                'range between the highest and the lowest death count from all causes in {}-{}'.format(
                    morta_year_bgd_notnull_min, morta_year_bgd_notnull_max)],
               title='left Y axis:', fontsize='small', handlelength=1.6, loc='upper left',
               bbox_to_anchor=(-0.0845, 1.3752))
    # TODO: There are countrie eg. Cuba, Argentina) which had lockdown stringency at 100, but 100 is not visible on the
    #  chart. Also 0% of postive results in Ecuador (bigus as it is) is not visible.
    axs2.legend(['lockdown stringency: 0 ~ none, 100 ~ full',
                 'percent of positive results in all COVID-19 tests',
                 'percent of people vaccinated in the country\'s populace',
                 'percent of people vaccinated fully in the country\'s populace'],
                title='right Y axis:', fontsize='small', handlelength=1.6, loc='upper right',
                bbox_to_anchor=(1.057, 1.375))

    axs.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1, byweekday=6))

    axs.set_xlabel(xlabel="date", loc="right")

    axs2.set(ylabel="percent",
             xlim=[df_merged_one['date'].head(1), df_merged_one['date'].tail(1)],
             ylim=[0, 100])

    axs2.yaxis.set_major_locator(mticker.MultipleLocator(10))

    axs.set(ylabel="number of people",
            xlim=[df_merged_one['date'].head(1), df_merged_one['date'].tail(1)],
            ylim=[y_min - (abs(y_max) - abs(y_min)) * 0.05, y_max + (abs(y_max) - abs(y_min)) * 0.05])

    axs2.set_xlabel(xlabel="date", loc="right")

    # Put the axs2 (the right Y axis) below the legend boxes. By default it would overlap the axs'es (left) legend box.
    # For more details see https://github.com/matplotlib/matplotlib/issues/3706.
    legend = axs.get_legend()
    axs.get_legend().remove()
    axs2.add_artist(legend)

    axs.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

    mpyplot.title("{}, {}".format(country, year), fontweight="bold", loc='right')

    mpyplot.figtext(0.065, 0,
                    'Data sources, via Our World in Data (https://ourworldindata.org, '
                    'https://github.com/owid/covid-19-data):\n'
                    '- All-cause mortality: Human Mortality Database Short-term Mortality Fluctuations project. '
                    'https://www.mortality.org and World Mortality Dataset. '
                    'https://github.com/akarlinsky/world_mortality\n'
                    '- COVID-19 mortality: Center for Systems Science and Engineering at Johns Hopkins University. '
                    'https://github.com/CSSEGISandData/COVID-19\n'
                    '- Lockdown stringency index: Hale, T. et al. A global panel database of pandemic policies (Oxford '
                    'COVID-19 Government Response Tracker). Nature Human Behaviour (2021). '
                    'https://doi.org/10.1038/s41562-021-01079-8\n'
                    '- Vaccinations: Mathieu, E. et al. A global database of COVID-19 vaccinations. Nature Human '
                    'Behaviour (2021). https://doi.org/10.1038/s41562-021-01122-8\n'
                    '- Testing: Hasell, J., Mathieu, E., Beltekian, D. et al. A cross-country database of COVID-19 '
                    'testing. Sci Data 7, 345 (2020). https://doi.org/10.1038/s41597-020-00688-8',
                    fontsize=6.5, va="bottom", ha="left", fontstretch="extra-condensed")

    # mpyplot.tight_layout(pad=1)

    fig.savefig('{}_{}.png'.format(country.replace(' ', '_'), year), bbox_inches="tight", pad_inches=0.05,
                pil_kwargs={'optimize': True})

    df_merged_one.to_csv('{}_{}.csv'.format(country.replace(' ', '_'), year), index=False)


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
                                    help='List countries available in both input CSV.')

    mutually_exclusive.add_argument('--country',
                                    help="Country to process - e.g. 'Poland'. Use 'ALL' to process all countries one by"
                                         " one.")

    parser.add_argument('--year',
                        required='--country' in sys.argv,
                        type=int,
                        help="Year to process - e.g. '2020'.")

    parser.add_argument('--dont_interpolate_week_53',
                        action='store_false',
                        dest='if_interpolate_week_53',
                        default=True,
                        help='Don\'t interpolate the historical 2010-2019 all-cause mortality at week 53 from data of '
                             'week 1 and 52, for 53-week years (eg. 2020). Such interpolation is enabled by default '
                             'because the OWID\'s excess_mortality.csv has its historical 2010-2019 all-cause mortality'
                             ' data capped at week 52.')

    parser.add_argument('--help', '-h',
                        action='help',
                        help='Show this help message.')

    args = parser.parse_args()

    main(args.country, args.year, args.if_list_countries, args.if_interpolate_week_53)

# TODO:
#  - Add a note on charts which helps finding it online after printing.
#  - Link few PNG charts in the README. Poland, US, Sweden, Belarus, Japan?
