# Upload Service — Functional Specification v1.2

## Revision history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-03-02 | Initial draft |
| 1.1 | 2026-04-10 | Added resumable uploads |
| 1.2 | 2026-05-21 | Virus scanning requirement |

## Purpose

The upload service accepts files from the web client and the mobile apps, stores them in object storage, and notifies the processing pipeline. This document specifies its externally visible behavior. Internal design is covered in the architecture document.

## Requirements

The service shall accept files up to 200 MB. Uploads larger than 10 MB must use the resumable protocol. The service shall reject any file whose declared type does not match its content. Every stored object shall be scanned for malware before the pipeline is notified, and a file that fails the scan shall be quarantined and reported to the uploader within one minute.

The service must respond to a completed upload within 500 ms at the 95th percentile under a load of 50 uploads per second.

## Example request

```
POST /uploads HTTP/1.1
Content-Type: application/pdf
Content-Length: 48213

<binary>
```

The response is `201 Created` with a JSON body containing the object id.

## Glossary

Resumable upload: an upload split into parts that can be retried individually. Object storage: the blob store behind the service.
