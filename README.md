## About the repository

This repository contains a Python script along with PNG charts and CSV datasets it creates, showing all-cause mortality
compared to COVID-19 mortality for a given country and year, in the context of lockdown stringency, vaccinations count,
virus testing, and the country's all-cause mortality in preceding years.

## How to use this

### Browse charts and their datasets, updated once in few weeks:

- To see all charts on a single page click this [CHARTS.md](CHARTS.md) link. Here's a sample for just 3 countries:

- To see only a single chart or dataset for a given country and year:

  - Enter directory [covid_toll_ALL](covid_toll_ALL) which contains charts (in PNG format) and data (in CSV format) for
    countries which have had their data in both the
    [excess_mortality.csv](https://github.com/owid/covid-19-data/blob/master/public/data/excess_mortality/excess_mortality.csv)
    and the [owid-covid-data.csv](https://github.com/owid/covid-19-data/blob/master/public/data/owid-covid-data.csv).

  - Click on any file. E.g. on the [covid_toll_ALL/Poland_2021.png](covid_toll_ALL/Poland_2021.png) to see the chart for
    Poland in 2021, or the [covid_toll_ALL/Poland_2021.csv](covid_toll_ALL/Poland_2021.csv) to see the chart's input
    data.

### Render most up-to-date charts and datasets yourself:

- Make sure you have `Python` 3.9 or newer with `Pandas` and `matplotlib` libraries installed.

- `git clone` this repository.

- `cd` to a directory where you have cloned it.

- Download these 2 datasets from the [OWID's GitHub repository](https://github.com/owid/covid-19-data) into that same 
  directory: 
  [excess_mortality.csv](https://github.com/owid/covid-19-data/blob/master/public/data/excess_mortality/excess_mortality.csv)
  and [owid-covid-data.csv](https://github.com/owid/covid-19-data/blob/master/public/data/owid-covid-data.csv).

- Run `./covid_toll_tool.py --help` to figure out how to proceed. The final product will be a PNG chart and a CSV 
  dataset for the `--country` and `--year` specified on the command line. E.g. `Poland_2020.png` and `Poland_2020.csv`,
  if `Poland` and `2020` were specified, respectively.

## About the data

All input data are provided by the [Our World in Data (OWID)](https://ourworldindata.org/) project under the
[Creative Commons BY license](https://creativecommons.org/licenses/by/4.0/).

`covid_toll_tool.py` doesn't alter the OWID's data in a meaningful way. It mainly aggregates the data that I find most
relevant and combines them on one chart per country/year, for a convenient visual analysis. You can verify the
identity of my charts' data against the original OWID's data using their [Data explorer](
https://ourworldindata.org/explorers/coronavirus-data-explorer?zoomToSelection=true&uniformYAxis=0&pickerSort=asc&pickerMetric=location&Metric=Cases%2C+tests%2C+positive+and+reproduction+rate&Interval=7-day+rolling+average&Relative+to+Population=true&Color+by+test+positivity=false&country=~POL).

The only information `covid_toll_tool.py`'s charts show that you won't find in the original OWID's data directly, is the
death count from all causes **excluding** deaths attributed to COVID-19 (black dashed line). It's derived as the
all-cause mortality minus the COVID-19 death toll. Viewed together with the all-cause mortality (black solid line) it
allows to assess the actual contribution of COVID-19 to country's overall mortality in a given period.

OWID obtain their data from official sources like government healthcare agencies and academic institutions. For more
information on particular datasets please visit the following resources:

1. All-cause mortality:
   - [Human Mortality Database Short-term Mortality Fluctuations project](https://www.mortality.org)
   - [World Mortality Dataset](https://github.com/akarlinsky/world_mortality)
2. COVID-19 mortality:
   - [Center for Systems Science and Engineering at Johns Hopkins University](https://github.com/CSSEGISandData/COVID-19)
3. Lockdown stringency index:
   - Hale, T. et al. A global panel database of pandemic policies (Oxford COVID-19 Government Response Tracker). Nature
     Human Behaviour (2021). https://doi.org/10.1038/s41562-021-01079-8
4. Vaccinations:
   - Mathieu, E. et al. A global database of COVID-19 vaccinations. Nature Human Behaviour (2021).
     https://doi.org/10.1038/s41562-021-01122-8
5. Testing:
   - Hasell, J., Mathieu, E., Beltekian, D. et al. A cross-country database of COVID-19 testing. Sci Data 7, 345 (2020).
     https://doi.org/10.1038/s41597-020-00688-8
