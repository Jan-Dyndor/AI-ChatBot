# File deletion lifecycle

This page describes the current `DELETE /v1/files/{file_id}` behavior. File
metadata in PostgreSQL is the source of truth for ownership and deletion state.
The file bytes live in local storage, and indexed chunks live in ChromaDB.
These three stores do not share a transaction.

## When deletion can start

The authenticated user must own the file. The database changes the record from
`READY` to `DELETING` only when `index_status` is `SUCCESS` or `FAILURE`. Both
conditions are checked in one conditional `UPDATE ... RETURNING` statement. A
second request cannot claim the same `READY` record after the first request
commits `DELETING`.

`PENDING` and `PROCESSING` indexing states block deletion. `FAILURE` permits
deletion because a failed indexing attempt may still have written some chunks.
A file whose `file_status` is `PROCESSING` is also ineligible, even if its
indexing status is terminal.

## Operation order

1. Atomically claim the owned file in PostgreSQL by setting `DELETING`, commit
   the change, and retain its storage path.
2. Remove the physical file. A missing file is treated as already removed.
3. Find ChromaDB chunks using both `user_id` and `file_id`, then delete the
   matching chunk IDs. An empty result is treated as already removed.
4. Delete the owned metadata record from PostgreSQL. Only after this step does
   the endpoint return `204 No Content`.

The record remains in PostgreSQL until the external cleanup steps finish. This
preserves the owner, file ID, and storage path needed to investigate or resume
a partial deletion. Once marked `DELETING`, the file cannot be downloaded
through the normal file endpoint.

## HTTP responses and partial failures

| Condition | Current response | Persisted result |
| --- | --- | --- |
| All steps finish | `204` with an empty body | File and metadata removed; chunks found during the ChromaDB lookup deleted. |
| File is absent or belongs to another user | `404` | No deletion starts. |
| File is already `DELETING` | `409` | The new request performs no cleanup. |
| Upload or indexing is unfinished | `405` | Record is unchanged; deletion can be retried once eligible. |
| Storage, ChromaDB, or final DB deletion fails | `500` | Earlier completed external steps stay completed. The record normally remains `DELETING`. |

After a successful deletion, repeating the HTTP request returns `404`. After a
partial failure, repeating it returns `409` because the record is already
`DELETING`. Individual cleanup operations tolerate an absent file, no matching
chunks, or an absent metadata row, but the HTTP endpoint does not currently
resume a `DELETING` record.

If the database connection fails during the final commit, the client may not
know whether that commit succeeded. Check the record before assuming it is
still present.

## Recovery work still planned

A scheduled Celery task is intended to find records that have remained
`DELETING` for a defined interval and retry cleanup of local storage, ChromaDB,
and PostgreSQL. **That task does not exist yet.** Until it is implemented, a
partial failure can leave a record in `DELETING` indefinitely and can block
uploading the same file content again because of the user's file SHA uniqueness
constraint.

The recovery task will need a deletion start timestamp, a way to prevent two
cleanup workers from claiming the same record, and a path that processes an
already `DELETING` record without trying to repeat the `READY` to `DELETING`
transition. The indexing status guard covers the normal single-task flow; it
does not by itself coordinate deletion with a duplicate or delayed Celery task
that might still write chunks.

## Tests

The HTTP behavior and failure states are covered in
[`tests/test_api_delete_file.py`](../tests/test_api_delete_file.py). Repository
claiming, concurrent claims, and repeatable cleanup steps are covered in
[`tests/test_file_deletion.py`](../tests/test_file_deletion.py). The concurrent
claim test uses SQLite, and ChromaDB is mocked; these tests do not prove
locking behavior on PostgreSQL or coordination with live Celery workers.
