# Academics

This application is a portal for gathering publication and metric
information about the academics associated with Leicester BRC from
the following scources:

* Scopus: https://www.scopus.com/
* Google Scolar (not implemented): https://scholar.google.com/
* Pubmed (not implemented): https://pubmed.ncbi.nlm.nih.gov/

## Scopus API

Data is pulled from the Scopus system using its
API (https://dev.elsevier.com/api_docs.html) using the
Elsapy python library (https://github.com/ElsevierDev/elsapy/wiki).

Authentication to the API uses an API key that is currently associated
with my (Richard Bramley) account, but at some point this can be changed
to use OAuth and the user's account.

## API

### API Key

To access the API the user will need to create an API Key in the Admin > Maintenance pages.

The API key should be added to the URL of an endpoint in the query string for the parameter `api_key`.
For example `https://academics.lbrc.le.ac.uk/api/publications?api_key=acab3c93-a9e7-4e28-83a0-258b298be5d0`

### Endpoints

All endpoints are read only and should be accessed using the HTTP GET method.

#### Publications

Endpoint
: https://academics.lbrc.le.ac.uk/api/publications

Returns summary publication data exactly the same as for the [publication reports](https://academics.lbrc.le.ac.uk/reports).

##### Parameters

**total**: Defines what the `buckets` will be in the output
**group_by**: Defines what the `series` will be in the output

To see what other parameters are available, see the `PublicationSummarySearchForm` class

Or go to the [publication reports](https://academics.lbrc.le.ac.uk/reports) to define your search and convert the
URL to the API endpoint.

##### Output
The output is returned as a JSON list.  Each item represents the number of publications found for the search criteria
split by the `total` and `group_by` fields.

#### Academics
Endpoint
: https://academics.lbrc.le.ac.uk/api/academics

Returns details of authors

##### Parameters

To see what parameters are available, see the `AcademicSearchForm` class

Or go to the [academic index page](https://academics.lbrc.le.ac.uk) to define your search and convert the
URL to the API endpoint.

##### Output
The output is returned as a JSON list.  Each item is details for an academic found for the search criteria.

## Running Jobs

This application uses background tasks to connect to the external
systems using the python Celery library with Redis as the backend.

### Redis Server

To run redis, use the command:

```
redis-server
```

### Run Celery Worker

To run the celery work, use the command:

```
celery -A celery_worker.celery worker -l 'INFO'
```

### Installation on MacOS (Dev only)

Installation of the cairo library must be done using homebrew
as these cannot be done using the pip installation processes

```
brew install cairo
brew install pango
```

If using mariadb as your database backend

```
brew install mariadb-connector-c
```