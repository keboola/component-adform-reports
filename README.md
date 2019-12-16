# Adform Reports extractor

Retrieve Buy-Side report data from the Reporting Stats API.

Reporting Stats API returns report data consisting of statistics derived from the data collected by the Adform tracking code. 
Each report is organized as dimensions and metrics. Metrics are the individual measurements of user activity on your property, 
such as impressions, clicks and conversions. Dimensions break down metrics across some common criteria, 
such as campaign or line item. When you build a query, you specify which dimensions 
and metrics you want in your report data.


**Table of contents:**  
  
[TOC]

# Configuration

## Authorization

- **API client secret**, **API client ID** - Adform client credentials for registered app with `Credentials flow` enabled.

## Result table name

Name of the Storage table where the result report data will be stored. The default is `report-data`.

## Load type

If set to Incremental update, the result tables will be updated based on primary key consisting of all selected dimensions. Full load overwrites the destination table each time, with no primary keys.

**Note**: When set to incremental updates the primary key is set automatically based on the dimensions selected. 
If the dimension list is changed in an existing configuration, the existing result table might need to be dropped or the primary key changed before the load, since it structure 
will be different. If set to full load, **no primary key** is set.

## Filter

### Date

Report date range boundaries. The maximum date range accessible through API is 397 days (13 months) from today.

### Client IDS

Optional list of client IDs to retrieve. If left empty, data for all available clients will be retrieved.

## Dimensions

List of report dimensions. For full list of dimensions and its' description refer [here](docs/available_dimensions.md)

## Source table
The table you wish to snapshot.
   
- `ID`-  e.g. "out.c-test_snapshot.out_table" - full ID of the source table that you want to snapshot
- `Primary Key` - Comma separated list primary key columns of the source table
- `Monitored parameters` - Comma separated list of columns that will be "monitored". This means that these columns 
will be checked for changes and a new (SCD2) snapshot will be created whenever a change is recognized.

 
## Development
 
This example contains runnable container with simple unittest. For local testing it is useful to include `data` folder in the root
and use docker-compose commands to run the container or execute tests. 

If required, change local data folder (the `CUSTOM_FOLDER` placeholder) path to your custom path:
```yaml
    volumes:
      - ./:/code
      - ./CUSTOM_FOLDER:/data
```

Clone this repository, init the workspace and run the component with following command:

```
git clone https://bitbucket.org:kds_consulting_team/kbc-python-template.git my-new-component
cd my-new-component
docker-compose build
docker-compose run --rm dev
```

Run the test suite and lint check using this command:

```
docker-compose run --rm test
```

# Integration

For information about deployment and integration with KBC, please refer to the [deployment section of developers documentation](https://developers.keboola.com/extend/component/deployment/) 