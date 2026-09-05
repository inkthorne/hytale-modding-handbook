# No Defaults

A corpus that BINDS but carries no Default column anywhere. The binder's own floor
does not fire here — there are pages, there are sections, and one of them resolves
to a real codec — so the only thing standing between this and a green `PASS` is the
gate's own zero-floor. That distinction is the whole reason this directory exists
separately from an empty one: an empty corpus trips the binder and never reaches
the gate, so testing the gate's floor with an empty directory tests the binder's.

### Widget

**Package:** `defpkg`

| Key | Type | Description |
|-----|------|-------------|
| `Radius` | double | No Default column, so nothing here is a defaults claim |
