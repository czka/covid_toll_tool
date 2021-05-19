## About

This is a Python script which creates PNG charts and CSV datasets of all-cause mortality compared to COVID-19 mortality, 
for a given country and year in the context of lockdown stringency and the country's all-cause mortality in preceding
years.

It uses 4 input datasets provided by the [Our World in Data (OWID)](https://ourworldindata.org/) project for open access
under the [Creative Commons BY license](https://creativecommons.org/licenses/by/4.0/):

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

## Usage

### To render up-to-date charts and datasets yourself:

- Make sure you have `Python` 3.9 or newer with `Pandas` and `matplotlib` libraries installed.

- `git clone` this repository.

- `cd` to a directory where you have cloned it.

- Download these 2 datasets from the [OWID's GitHub repository](https://github.com/owid/covid-19-data) into that same 
  directory: 
  [excess_mortality.csv](https://github.com/owid/covid-19-data/blob/master/public/data/excess_mortality/excess_mortality.csv)
  and [owid-covid-data.csv](https://github.com/owid/covid-19-data/blob/master/public/data/owid-covid-data.csv).

- Run `./covid_toll_tool.py --help` to figure out how to proceed. The final product will be a PNG chart and a CSV 
  dataset for the `--country` and the `--year` specified on the command line - e.g. `Poland_2020.png` and 
  `Poland_2020.csv`.

### To explore charts and datasets I have already published with the script:

- Enter directory [covid_toll_ALL] which contains the script's charts (in PNG format) and data (in CSV format) for the
  countries which have had their data in both the
  [excess_mortality.csv](https://github.com/owid/covid-19-data/blob/master/public/data/excess_mortality/excess_mortality.csv)
  and the [owid-covid-data.csv](https://github.com/owid/covid-19-data/blob/master/public/data/owid-covid-data.csv).
  
- Click on any file. E.g. on the [covid_toll_ALL/Poland_2020.png] to see the chart for Poland in 2020.

- Directories [covid_toll_2020](covid_toll_2020) and [covid_toll_2021](covid_toll_2021) contain links to PNG and CSV 
  files in [covid_toll_ALL](covid_toll_ALL) for a given year.
