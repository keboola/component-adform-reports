# Adform Reports extractor

Retrieve Buy-Side report data from the [Reporting Stats API](https://api.adform.com/help/guides/how-to-report-on-campaigns/reporting-stats).
    
Reporting Stats API returns report data consisting of statistics derived from the data collected by the Adform tracking code. 
Each report is organized as dimensions and metrics. Metrics are the individual measurements of user activity on your property, 
such as impressions, clicks and conversions. Dimensions break down metrics across some common criteria, 
such as campaign or line item. When you build a query, you specify which dimensions 
and metrics you want in your report data.


**Table of contents:**  
  
[TOC]

# Prerequisites

To use this extractor the user is required to register a client application using the `Credentials flow` authentication. 

To register the application follow the steps described in the [official documentation](https://api.adform.com/help/guides/getting-started/authorization-guide#prerequisites):

Contact Adform API support (technical@adform.com) and provide the **following information**:

- short description of your application (Adform's API use case): `Retrieve Buy-Side report data from the Reporting Stats API`
- authorization flow: `client credentials`
- a list of needed scopes for application: `https://api.adform.com/scope/buyer.stats`

You will then receive your `client secret` and `client id` that will be used for the authentication.


# Configuration

## Authorization

- **API client secret**, **API client ID** - Adform client credentials for registered app with the `Client credentials flow` enabled.

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

List of report dimensions. For full list of dimensions and its' description [refer here](docs/available_dimensions.md). 
Or can be retrieved using this [API call](https://api.adform.com/help/references/buyer-solutions/reporting/metadata/dimensions) 

## Metrics

List of report metrics. Max 10. Note that some combinations of metrics and/or dimensions are not supported.

Each metric definition consists of a **metric name** and additional filtering possibilities (`Specs Metadata`) for individual metric. 
If no value is specified in the `Specs Metadata` the default metric is used.

For a full list of available metrics and specs [see here](https://bitbucket.org/kds_consulting_team/kds-team.ex-adform-reports/raw/a5e14ac3450e4e1ab5b3cdb061493e2d5078108f/docs/available_metrics.md)
Or can be retrieved using thi [API call](https://api.adform.com/help/guides/how-to-report-on-campaigns/reporting-stats/metrics)
 
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