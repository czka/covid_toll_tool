#!/usr/bin/env python3

"""
Use OWID's data to create PNG charts and CSV datasets of all-cause mortality compared to COVID-19 mortality, for a given
country and year in the context of a country's all-cause mortality in preceding years.
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
    mortality_cols = ['deaths_2010_all_ages', 'deaths_2011_all_ages', 'deaths_2012_all_ages', 'deaths_2013_all_ages',
                      'deaths_2014_all_ages', 'deaths_2015_all_ages', 'deaths_2016_all_ages', 'deaths_2017_all_ages',
                      'deaths_2018_all_ages', 'deaths_2019_all_ages']

    covid_cols = ['location', 'date', 'new_cases_smoothed', 'new_tests_smoothed', 'new_deaths', 'stringency_index',
                  'people_vaccinated', 'people_fully_vaccinated', 'population']

    death_cols = ['location', 'date', 'time', 'time_unit'] + mortality_cols + \
                 ['deaths_2020_all_ages', 'deaths_2021_all_ages']

    df_covid_all = pd.read_csv("./owid-covid-data.csv", parse_dates=['date'], usecols=covid_cols).reindex(
        columns=covid_cols)

    df_death_all = pd.read_csv("./excess_mortality.csv", parse_dates=['date'], usecols=death_cols).reindex(
        columns=death_cols)

    common_countries = ['ALL'] + sorted(set(df_death_all['location']) & set(df_covid_all['location']))

    if if_list_countries:
        list_countries(common_countries)

    elif country == 'ALL':
        for country in common_countries:
            get_it_together(country, df_covid_all, df_death_all, year, mortality_cols, if_interpolate_week_53)

    elif country in common_countries:
        get_it_together(country, df_covid_all, df_death_all, year, mortality_cols, if_interpolate_week_53)

    else:
        print("Country '{}' is not present in both input datasets.\n".format(country))
        list_countries(common_countries)


def list_countries(common_countries):
    print("Please set '--country' to one of the following {} countries present in both input datasets, or 'ALL', to "
          "process them all one by one: {}.".
          format(len(common_countries)-1, ', '.join("'{}'".format(c) for c in common_countries)))


def get_it_together(country, df_covid_all, df_death_all, year, mortality_cols, if_interpolate_week_53):
    # Take only rows for the specified country.
    df_covid_one = df_covid_all[df_covid_all['location'] == country].copy().reset_index(drop=True)
    df_death_one = df_death_all[df_death_all['location'] == country].copy().reset_index(drop=True)

    if df_death_one['time_unit'].nunique() == 1:

        # Create ISO-week date index, starting at the end (7 = Sunday) of the 1st week of a year, and ending at the end
        # of the 1st week of the following year. So that there's a 1 week overlap between charts for subsequent years -
        # (eg. a 2020 chart will also have the 1st week of 2021). By ISO specification the 28th of December is always
        # in the last week of the year.

        # weekly_death_index_1 = pd.date_range(start='2020', end='2021', freq='W')
        weekly_death_index = [ddatetime.fromisocalendar(2020, i, 7).strftime('%Y-%m-%d')
                              for i in range(1, ddate(2020, 12, 28).isocalendar().week + 1)] + \
                             [ddatetime.fromisocalendar(2021, 1, 7).strftime('%Y-%m-%d')]

        # weekly_covid_index_1 = pd.date_range(start=str(year), end=str(year + 1), freq='W')
        weekly_covid_index = [ddatetime.fromisocalendar(year, i, 7).strftime('%Y-%m-%d')
                              for i in range(1, ddate(year, 12, 28).isocalendar().week + 1)] + \
                             [ddatetime.fromisocalendar(year + 1, 1, 7).strftime('%Y-%m-%d')]

        # weekly_death_index_2 = pd.date_range(start='2021', periods=1, freq='W')
        # weekly_death_index_2 = ddatetime.fromisocalendar(2021, 1, 7).strftime('%Y-%m-%d')
        # weekly_covid_index_2 = pd.date_range(start=str(year + 1), periods=1, freq='W')
        # weekly_covid_index_2 = ddatetime.fromisocalendar(year + 1, 1, 7).strftime('%Y-%m-%d')

        # weekly_death_index = weekly_death_index_1.append(weekly_death_index_2)
        # weekly_covid_index = weekly_covid_index_1.append(weekly_covid_index_2)

        # df_weekly_death_index = weekly_death_index.to_frame(index=False, name='date')
        # df_weekly_covid_index = weekly_covid_index.to_frame(index=False, name='date')
        df_weekly_death_index = pd.DataFrame(weekly_death_index, columns=['date'], dtype='datetime64[ns]')
        df_weekly_covid_index = pd.DataFrame(weekly_covid_index, columns=['date'], dtype='datetime64[ns]')

        # print(df_weekly_death_index, "\n", df_weekly_covid_index)

        if df_death_one['time_unit'].unique()[0] == 'monthly':

            # Interpolate monthly mortality data to weekly so that they can be visualized together with other weekly
            # data.
            df_death_one = df_death_one.set_index('date').resample(rule='W').first().interpolate(limit_area='inside').\
                reset_index()
            # Prepend 'date' column with 4 initial week dates missing (2020-01-05, 2020-01-12, 2020-01-19,
            # 2020-01-26), as the 1st month-date we get after resampling month dates to week dates is 2020-02-02.
            df_death_one = df_weekly_death_index[0:4].append(df_death_one, ignore_index=True)

            # TODO: Update the whole 'time_unit' column to 'monthly'?

        df_deaths_during_covid = df_death_one[['date']].copy()

        # Take only rows of the given year.
        df_death_one = pd.merge(left=df_weekly_death_index, right=df_death_one, on='date', how='left')

        # deaths_during_covid = df_death_one['deaths_2020_all_ages'].dropna().append(
        #     df_death_one['deaths_2021_all_ages'], ignore_index=True)
        # TODO: Explain [0:-1]
        df_deaths_during_covid['deaths_during_covid'] = df_death_one['deaths_2020_all_ages'][0:-1].append(df_death_one['deaths_2021_all_ages'], ignore_index=True)

        df_merged_one, mortality_cols, y_min, y_max = process_weekly(df_covid_one, df_death_one, df_weekly_covid_index,
                                                                     df_deaths_during_covid, year, mortality_cols,
                                                                     if_interpolate_week_53)

        plot_weekly(df_merged_one, country, year, mortality_cols, y_min, y_max)


def process_weekly(df_covid_one, df_death_one, df_weekly_covid_index, df_deaths_during_covid, year, mortality_cols, if_interpolate_week_53):
    # For some reason the vaccinated counts are missing for a number of dates. Filling them in with a linear
    # interpolation between the 2 known closest values.
    df_covid_one['people_vaccinated'].interpolate(limit_area='inside', inplace=True)
    df_covid_one['people_fully_vaccinated'].interpolate(limit_area='inside', inplace=True)

    # Gaps happen in lockdown stringency data, too. OWID only take them from the OxCGRT project as they are (see eg.
    # https://github.com/owid/covid-19-data/issues/1961#issuecomment-918357447).
    df_covid_one['stringency_index'].interpolate(limit_area='inside', inplace=True)

    # We need to resample the daily covid data to match the weekly mortality data, with week date on Sunday.
    # resample().sum() removes any input non-numeric columns, ie. `location` here, but we don't need it. It also "hides"
    # the `date` column by setting an index on it, but we are going to need this column later on, thus bringing it back
    # with reset_index().
    df_covid_one = df_covid_one.resample(rule='W', on='date').agg(
        {'new_deaths': 'sum',
         'new_cases_smoothed': 'mean',
         'new_tests_smoothed': 'mean',
         'stringency_index': 'mean',
         'people_vaccinated': 'mean',
         'people_fully_vaccinated': 'mean',
         'population': 'mean'}
    ).reset_index()

    df_covid_one['positive_test_percent'] = \
        df_covid_one['new_cases_smoothed'] / df_covid_one['new_tests_smoothed'] * 100

    df_covid_one['people_vaccinated_percent'] = \
        df_covid_one['people_vaccinated'] / df_covid_one['population'] * 100

    df_covid_one['people_fully_vaccinated_percent'] = \
        df_covid_one['people_fully_vaccinated'] / df_covid_one['population'] * 100

    y_min, y_max = find_yrange_weekly(df_covid_one, df_death_one)

    # Pre-covid mortality counts in excess_mortality.csv (starting at 2010, 2011, 2015 or 2016 for some countries,
    # ending at 2019) are only present in the 2020's rows. So we have to always use the 2020's data, also if creating a
    # chart for e.g. 2021. If args.year was > 2020 move week dates ahead as needed.
    df_death_one['date'] = df_death_one['date'] + pd.DateOffset(years=year - 2020)

    # If a DateOffset was applied, move the week's date to an *actual Sunday* of the given year. Not altering the data
    # in any way, just taking the first value (as we are resampling weekly to weekly there's *only* one, so e.g. last()
    # would work as well), and using the resultant DatetimeIndex items which resample() set to weeks' Sundays of the
    # args.year, to update the `date` column. Does nothing if args.year == 2020. dropna() deals with weekly datasets
    # which don't follow the ISO week numbering (the only such case currently is Tunisia - capped at week 52 even in
    # 2020, see https://github.com/akarlinsky/world_mortality/issues/7 for details), or otherwise incomplete.
    df_death_one['date'] = df_death_one.resample(rule='W', on='date').first().dropna(how='all').index
    # If dates changed, week numbers could use an update to compensate for 2020's 53 weeks vs e.g. 2021's 52; just for
    # the sake of it, as `df_death_one[df_death_one['date'].dt.isocalendar().year` will trim at week 52 anyway. Does
    # nothing if args.year == 2020.
    df_death_one['time'] = df_death_one['date'].dt.isocalendar().week

    # Take only rows of the given year. `dt.isocalendar().year` automagically takes 52/53 weeks a year into account.
    # df_covid_one = df_covid_one[df_covid_one['date'].dt.isocalendar().year == year]
    # df_death_one = df_death_one[df_death_one['date'].dt.isocalendar().year == year]
    print(df_covid_one)
    # Take only rows of the given year.
    df_covid_one = pd.merge(left=df_weekly_covid_index, right=df_covid_one, on='date', how='left')
    # Merge death count during covid *demics in a given year into the covid DataFrame.
    df_covid_one = pd.merge(left=df_covid_one, right=df_deaths_during_covid, on='date', how='left')
    # df_covid_one['deaths_during_covid'] = deaths_during_covid

    # print(df_death_one)
    print(df_covid_one)

    # Add week of year column based on the week date resampled from day dates (not used - just for parity with the
    # mortality dataframe).
    df_covid_one['time'] = df_covid_one['date'].dt.isocalendar().week

    # Merge both datasets now that they are aligned on their dates.
    df_merged_one = pd.merge(df_death_one, df_covid_one, how='inner')

    # Exclude the mortality columns which have no data. E.g. many countries have data only for 2015-2019.
    mortality_cols = [col for col in mortality_cols if df_merged_one[col].notnull().values.any()]
    print('mortality_cols after exclude:')
    print(mortality_cols)
    df_merged_one['deaths_min'] = df_merged_one[mortality_cols].min(axis=1)
    df_merged_one['deaths_max'] = df_merged_one[mortality_cols].max(axis=1)
    df_merged_one['deaths_mean'] = df_merged_one[mortality_cols].mean(axis=1)

    # A year is typically 52 weeks. Some years, e.g. 2015 and 2020, are 53 weeks (see e.g.
    # https://www.timeanddate.com/date/week-numbers.html). All-cause mortality data in excess_mortality.csv for
    # 2010-2019 are capped at week 52 regardless of that. There are 3 ways to mitigate this I can think of:
    # 1. Trim all-cause and covid data at week 52 for all years, always. This means e.g. losing data in 2020. Not really
    # an option.
    # 2. Have mortality graph for 2020 stand out of the historical background mortality graph by 1 week, and deal with
    # the missing historical mortality data at week 53 in any calculations for 2020. Better, but I'd rather avoid
    # producing charts which seem incomplete/corrupted at the last week of a year, as well as complicating the code that
    # would be simpler if mortality data in a given year and in previous years were symmetrical. If that's what the user
    # prefers however, there's the `--dont_interpolate_week_53` to enable such behaviour for charts rendering. It used
    # to be the default.
    # 3. Interpolate the historical all-cause mortality at week 53 from week's 1 and 52 data. This is the current
    # default. I don't think this is too much of a stretch - a year is a circle after all... Let me know if you think
    # that's wrong. Mind that OWID themselves just assume the average at week 53 equals the average at week 52, and
    # apparently even that is good enough (see e.g.
    # https://ourworldindata.org/grapher/excess-mortality-raw-death-count?tab=chart&stackMode=absolute&country=~POL&region=World).

    # By ISO specification the 28th of December is always in the last week of the year.
    weeks_count = ddate(year, 12, 28).isocalendar().week

    if if_interpolate_week_53 and weeks_count == 53:
        df_merged_one.loc[52, 'deaths_min'] = (df_merged_one['deaths_min'][0] + df_merged_one['deaths_min'][51]) / 2
        df_merged_one.loc[52, 'deaths_max'] = (df_merged_one['deaths_max'][0] + df_merged_one['deaths_max'][51]) / 2
        df_merged_one.loc[52, 'deaths_mean'] = (df_merged_one['deaths_mean'][0] + df_merged_one['deaths_mean'][51]) / 2

    df_merged_one['deaths_noncovid'] = df_merged_one['deaths_during_covid'].sub(
        df_merged_one['new_deaths'], fill_value=None)

    return df_merged_one, mortality_cols, y_min, y_max


def find_yrange_weekly(df_covid_one, df_death_one):
    """
    Find the Y axis bottom and top value in all-time OWID's data for a given country with weekly resolution of
    historical mortality data; to have an identical Y axis range on that country's charts in different years.
    """
    deaths_noncovid_mins = []
    deaths_noncovid_maxs = []

    # This loop calculates the number of non-covid deaths *for each year* covered in the OWID's data, to be able to
    # include it when calculating the Y axis value range. For some countries the number of non-covid deaths in a given
    # year (e.g. Belgium in 2020) happens to be lower than the lowest number of deaths from all causes in previous
    # years. For some, it's higher than the highest number of deaths in previous years - probably due to borked data,
    # but anyway (e.g. Kyrgyzstan in 2020).
    for y in df_covid_one['date'].dt.isocalendar().year.unique():
        # See process_weekly comments for explanations. This is mostly a copy-paste from there.
        df_covid_one_tmp = df_covid_one.copy()
        df_death_one_tmp = df_death_one.copy()

        df_death_one_tmp['date'] = df_death_one_tmp['date'] + pd.DateOffset(years=y - 2020)
        df_death_one_tmp['date'] = df_death_one_tmp.resample(rule='W', on='date').first().dropna(how='all').index

        df_death_one_tmp['time'] = df_death_one_tmp['date'].dt.isocalendar().week

        df_covid_one_tmp = df_covid_one_tmp[df_covid_one_tmp['date'].dt.isocalendar().year == y]
        df_death_one_tmp = df_death_one_tmp[df_death_one_tmp['date'].dt.isocalendar().year == y]

        df_covid_one_tmp['time'] = df_covid_one_tmp['date'].dt.isocalendar().week

        df_merged_one = pd.merge(df_death_one_tmp, df_covid_one_tmp, how='outer')

        df_merged_one['deaths_noncovid'] = df_merged_one['deaths_{}_all_ages'.format(y)].sub(
            df_merged_one['new_deaths'], fill_value=None)

        if df_merged_one['deaths_noncovid'].notnull().any():
            deaths_noncovid_mins.append(df_merged_one['deaths_noncovid'].min())
            deaths_noncovid_maxs.append(df_merged_one['deaths_noncovid'].max())

    if deaths_noncovid_mins:
        y_min = min(*deaths_noncovid_mins, df_merged_one.filter(regex='deaths_.*_all_ages').min().min())
    else:
        y_min = df_merged_one.filter(regex='deaths_.*_all_ages').min().min()

    if deaths_noncovid_maxs:
        y_max = max(*deaths_noncovid_maxs, df_merged_one.filter(regex='deaths_.*_all_ages').max().max())
    else:
        y_max = df_merged_one.filter(regex='deaths_.*_all_ages').max().max()

    return y_min, y_max


def plot_weekly(df_merged_one, country, year, mortality_cols, y_min, y_max):
    min_deaths_year = mortality_cols[0].split('_')[1]
    max_deaths_year = mortality_cols[-1].split('_')[1]

    fig, axs = mpyplot.subplots(figsize=(13.55, 5.75))  # Create an empty matplotlib figure and axes.

    axs2 = axs.twinx()

    df_merged_one.plot(x_compat=True, kind='line', use_index=True, grid=True, rot='50',
                       color=['royalblue', 'grey', 'red', 'black', 'black'], style=[':', ':', ':', '-', '--'],
                       ax=axs, x='date', y=['deaths_min', 'deaths_mean', 'deaths_max',
                                            'deaths_during_covid', 'deaths_noncovid'])

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

    axs.legend(['lowest death count in {}-{} from all causes'.format(min_deaths_year, max_deaths_year),
                'average death count in {}-{} from all causes'.format(min_deaths_year, max_deaths_year),
                'highest death count in {}-{} from all causes'.format(min_deaths_year, max_deaths_year),
                'death count in {} from all causes'.format(year),
                'death count in {} from all causes MINUS the number of deaths attributed to COVID-19'.format(year),
                'range between the highest and the lowest death count from all causes in {}-{}'.format(
                    min_deaths_year, max_deaths_year)],
               title='left Y axis:', fontsize='small', handlelength=1.6, loc='upper left',
               bbox_to_anchor=(-0.0845, 1.3752))

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
#  - Add per-million counts.
