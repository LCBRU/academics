# Academics

## Running Jobs

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
