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