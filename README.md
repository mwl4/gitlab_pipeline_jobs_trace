# GitLab Pipeline Jobs Trace

Tool which generates json trace file from GitLab pipeline to be used in chrome://tracing/ or https://ui.perfetto.dev/  
Useful when you need to optimize pipeline time and you have multiple runners running jobs in parallel.

![Chrome Trace](doc/chrome_trace.png "Chrome Trace")

![Perfetto Trace](doc/perfetto_trace.png "Perfetto Trace")

## Requirements

- Python >3.2
- GitLab (can be self hosted)
- GitLab Personal Access Token

To obtain Access Token go to `YOUR_GITLAB_URL/-/user_settings/personal_access_tokens` and generate token with `api` scope.

## Usage

You can provide GitLab URL and Access Token in two ways:
1. Environment variables: `GITLAB_URL`, `GITLAB_PRIVATE_TOKEN` 

2. `.secret.json` file in script directory:
```json
{
    "GITLAB_URL": "https://YOUR_GITLAB_URL.com",
    "GITLAB_PRIVATE_TOKEN": "glpat-XXXXXXXXXXXXXX-XXXXX"
}
```

Then use tool:

```
py tracing.py <PROJECT_ID> <PIPELINE_ID>
```

If your project ID is 123, and pipeline ID which you want to examine is 1234567, then:
```
py tracing.py 123 1234567
```

By default result is written to file:
```
Success: pipeline_trace_123_1234567.json
Load file in chrome://tracing/ or https://ui.perfetto.dev/
```

Then open chrome://tracing/ in your Chrome, and load generated json file.
You can also use https://ui.perfetto.dev/

Use `--out-file` parameter to output result to different file.  
Use `--to-stdout` switch to output result to standard output.

## Notes

Jobs are coloured basing on chosen runner. So that you can easily see which runner peeked the job and what other jobs the same runner was processing in the same time. Custom coloring functionality does not seem to be working on https://ui.perfetto.dev/ though.

Enjoy
