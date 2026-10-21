# 0001 — Hexagonal architecture and removal of model polymorphism

Status: proposed · 2026-10-21

## Question

Which boundaries let NeuroVault's rules for collections, images and analyses run
without Django, Celery, FreeSurfer or the local filesystem, and how do we replace
the django-polymorphic item hierarchy with composition without changing the public
API or losing data?

## Decisions already made

| # | Decision | Source |
|---|----------|--------|
| D1 | Full hexagon: domain entities are plain Python, persistence is an adapter. | user |
| D2 | Composition replaces inheritance, in the domain **and** in the database (django-polymorphic is removed). | user |
| D3 | Public API response shape is unchanged (`image_type` strings, field names, ids, URLs). | user |
| D4 | Existing plain `Image` rows (polymorphic type `image`) become `kind="other"`. | user |
| D5 | The data migration runs in a maintenance window; no dual-write period. | user |
| D6 | Django models stay in `apps/statmaps` (app label `statmaps`) and become the persistence adapter, so the migration history continues unbroken. | this doc |
| D7 | Item permissions are derived from the collection; per-item guardian rows are dropped. | this doc, evidence in §7 |
| D8 | Reads stay on the ORM (CQRS-lite): templates, datatables and API representations read ORM rows; every write goes through a use case. About 40 templates read model attributes and none are tested, so rendering from entities would be an untested rewrite with no architectural gain. | implementation |
| D9 | The composition root is `neurovault/bootstrap.py`, outside `application/`, so the application layer never imports adapters. | implementation |
| D10 | The dependency rule is enforced by a unit test (`application/tests/test_layering.py`) rather than import-linter, avoiding a new dependency. | implementation |
| D11 | Input validation (types, choices, required fields, error wording) stays in Django forms and DRF serializers; domain rules (quality checks, DOI resolution, bundle naming, file layout) run in the use cases those adapters call. Forms no longer save: `image_changes(form)` reads back what `construct_instance` applied and the view passes it to the use case. | implementation |

## 1. Current state

Business rules are spread across the framework's extension points instead of being
in one layer:

| Where | What | Reference |
|-------|------|-----------|
| `Image.save()` | queues `process_map`, moves files when the collection changes, infers species | `apps/statmaps/models.py:1210` |
| `BaseStatisticMap.save()` | opens the NIfTI with nibabel to infer `map_type`, deletes stale comparisons | `apps/statmaps/models.py:1380` |
| `BaseCollectionItem.save()/delete()` | bumps `collection.modify_date` | `apps/statmaps/models.py:975` |
| `Collection.delete()`, NIDM `post_delete` | removes directories from disk | `apps/statmaps/models.py:835`, `:1576` |
| `post_save` / `m2m_changed` signals | grant and revoke guardian permissions | `apps/statmaps/models.py:851-889`, `:991` |
| `ImageValidationMixin.clean_and_validate` | FreeSurfer `mris_convert` subprocess, AFNI 4D split | `apps/statmaps/forms.py:458` |
| `ImageSerializer.validate` | reuses the form mixin by faking `_errors = ErrorDict()` | `api/serializers.py:138` |
| `upload_folder` view | whole ingest flow: archive extraction → NIfTI discovery → atlas XML match → image creation | `apps/statmaps/views.py:925` |
| `NeuroVaultStorage.url()` | queries `Collection` to build a URL | `apps/statmaps/storage.py:22` |
| `get_paper_properties` | inline CrossRef HTTP call | `apps/statmaps/utils.py:214` |

Polymorphism: `BaseCollectionItem(PolymorphicModel)` → `Image` → (`BaseStatisticMap`
[abstract] → `StatisticMap`, `NIDMResultStatisticMap`) | `Atlas`; and
`BaseCollectionItem` → `NIDMResults`. Five tables plus the base table. Polymorphism
is consumed through 17 `instance_of` querysets, about 8 `polymorphic_ctype` checks,
`isinstance` dispatch in `ImageSerializer.to_representation`, the polymorphic admin,
`PolymorphicImageForm` and `ObjectOnlyPolymorphicPermissions`.

Tests: 67, all on `TestCase`/`APITestCase` (database required). No unit tests.

Two existing pieces already have the target shape and are followed here:
`apps/statmaps/meta.py` (a use-case module: gather → run → save) and the Celery tasks
(they take a primary key and load the object, as a driving adapter should).

## 2. Layers and packages

```
neurovault/
  domain/            entities, value objects, pure domain services (no Django imports)
    items.py         CollectionItem, StatMap, Atlas, OtherImage, NIDMBundle, ...
    collection.py    Collection aggregate and its value objects
    nifti.py         infer_map_type, is_thresholded, detect_4D, not_in_mni (pure, take arrays/affines)
    access.py        AccessPolicy (derived from collection owner/contributors/private)
  application/
    ports.py         Protocols for driven ports (§4)
    services/        use cases (§5), one module per aggregate
    bootstrap.py     composition root: wires adapters into services
  adapters/
    persistence/     repositories + mappers over the Django ORM (models stay in apps/statmaps)
    storage/         LocalMapStore (today's PRIVATE_MEDIA_ROOT layout)
    queue/           CeleryTaskQueue
    neuroimaging/    FreeSurferProjector, NilearnThumbnailRenderer, NiMAREEngine
    external/        CrossRefLookup, CognitiveAtlasGateway, DjangoEmailNotifier
  apps/statmaps/     web adapter (views, forms, templates) + ORM models (persistence adapter)
  api/               DRF adapter
```

Dependency rule: `domain` imports nothing from the project; `application` imports
`domain` only; adapters import `application` and `domain`. Enforced with
`import-linter` contracts in CI.

## 3. Domain model (composition)

```python
@dataclass
class CollectionItem:                    # an image of any kind
    id: ItemId
    collection_id: CollectionId
    name: str
    description: str
    files: ImageFiles                    # file, nifti_gz, surfaces, thumbnail, reduced_representation
    space: TemplateSpace                 # target_template_image, subject_species, data_origin
    subject: SubjectInfo                 # age, sex, handedness, BMI, ... (Image demographics)
    figure: str | None
    extra: dict                          # Image.data JSON
    tags: frozenset[Tag]
    is_valid: bool
    added: datetime
    modified: datetime
    payload: StatMap | Atlas | OtherImage

@dataclass
class StatMap:
    stats: MapStats                      # map_type, analysis_level, number_of_subjects,
                                         # is_thresholded, perc_bad_voxels, not_mni,
                                         # brain_coverage, perc_voxels_outside
    annotation: Annotation | None        # modality, smoothness, statistic params, ignore-warning,
                                         # + paradigm: CognitiveParadigm (contrast, cogatlas FKs, ...)
    source: NIDMProvenance | None        # replaces NIDMResultStatisticMap.nidm_results
                                         # invariant: exactly one of annotation / source

@dataclass
class Atlas:
    label_file: MapRef

@dataclass
class OtherImage: ...                    # D4

@dataclass
class NIDMBundle:                        # not an image; produces StatMaps
    id: BundleId
    collection_id: CollectionId
    name: str
    zip_file: MapRef
    ttl_file: MapRef | None
```

`Collection` becomes an aggregate of value objects that already exist as form
fieldsets (`apps/statmaps/forms.py:78-315`): `Essentials`, `Participants`, `Design`,
`Acquisition`, `Registration`, `Preprocessing`, `FirstLevel`, `GroupLevel`,
`Nutritional`, plus owner, contributors, privacy and DOI. Its rules (blank DOI →
None, `doi_add_date` on first public DOI, private token generation) move out of
`Collection.save()` and `get_absolute_url()` into the aggregate.

## 4. Driven ports

| Port | Responsibility | First adapter | Replaces |
|------|----------------|---------------|----------|
| `ImageRepository`, `BundleRepository`, `CollectionRepository` | load and save aggregates | Django ORM + mappers | direct ORM use in views, tasks, forms |
| `UnitOfWork` | transaction boundary, collects domain events | `transaction.atomic` | implicit autocommit |
| `MapStore` | put, open, move and delete map files; resolve public URLs | `LocalMapStore` | 185 `.path` uses, `NeuroVaultStorage.url()` ORM lookup |
| `TaskQueue` | enqueue `process_map` and similar jobs | `CeleryTaskQueue` | `apply_async` in `save()` |
| `SurfaceProjector` | surface files → volume | `FreeSurferProjector` | subprocess in `ImageValidationMixin` |
| `ThumbnailRenderer` | glass brain and surface images | nilearn | `tasks.generate_glassbrain_image` |
| `MetaAnalysisEngine` | IBMA over maps | NiMARE | `meta.run_meta_analysis` |
| `PublicationLookup` | DOI → title, authors, journal, date | CrossRef | `utils.get_paper_properties` |
| `OntologyGateway` | Cognitive Atlas tasks and contrasts | cognitiveatlas client | `tasks.repopulate_cognitive_atlas` |
| `Notifier` | email | Django mail | `utils.send_email_notification` |
| `AccessPolicy` | who can view, change or delete | domain service over the collection | guardian per-item rows, `ObjectOnlyPolymorphicPermissions` |

Guardian stays only as the storage behind collection-level permissions.

## 5. Use cases (driving side)

| Use case | Absorbs |
|----------|---------|
| `ingest_upload(collection, files)` | `upload_folder`, `ImageValidationMixin`, `ImageSerializer.validate/save`, `create_image_from_nifti`, AFNI split, surface projection |
| `ingest_nidm(collection, zip)` | `NIDMResultsForm.save`, `save_nidm_statmaps`, `populate_nidm_results` |
| `edit_item(item, changes)` | `edit_image` view, `EditableStatisticMapSerializer`, `edit_metadata` |
| `move_item(item, target_collection)` | file move in `Image.save()` |
| `delete_item`, `delete_collection` | `delete()` overrides, NIDM `post_delete` signal |
| `publish_collection`, `set_doi` | `Collection.save()` rules, `get_absolute_url()` token side effect |
| `set_contributors` | `contributors_changed` signal |
| `process_item(item_id)` | `tasks.process_map` (the task body becomes a call to this) |
| `find_similar(item_id)` | `utils.get_similar_images`, comparison tasks |
| `run_metaanalysis(id)` | `meta.py`, `finalize_metaanalysis` view |

Driving adapters (Django views, DRF views, Celery tasks, management commands, admin
actions) translate input into a use-case call and translate the result back. The
Django admin stays on the ORM models as a back-office tool and is the one adapter
allowed to bypass the use cases.

## 6. Persistence schema without polymorphism

Two tables replace six:

**`statmaps_item`** (images; ORM model `Item`): every column of `basecollectionitem` + `image`, the 8
`BaseStatisticMap` columns, the 11 `StatisticMap` columns, `atlas.label_description_file`,
and:

- `kind` varchar, one of `statmap`, `atlas`, `other`
- `source_bundle_id` nullable FK → `statmaps_nidmbundle` (was `NIDMResultStatisticMap.nidm_results`)

CheckConstraints:
- `kind='atlas'` ⇒ `label_description_file` is not null
- `kind<>'statmap'` ⇒ the statmap and paradigm columns are null
- `source_bundle_id` is not null ⇒ `kind='statmap'` and the paradigm columns are null

**`statmaps_nidmbundle`** (ORM model `NIDMBundle`): `basecollectionitem` columns + `zip_file`, `ttl_file`.

Ids: each row keeps its `basecollectionitem.id`. URLs, API ids, `Comparison.image1/2`,
`Metaanalysis.maps` and on-disk paths stay valid. Both new sequences start at
`max(basecollectionitem.id) + 1`, so no new id reuses an old one. After that, ids are
unique within each table only: an image and a bundle created later can share a
number. Nothing needs a shared id space: images and bundles have separate URLs
and API endpoints, tags are keyed by content type, and per-item permissions are
gone.

Foreign keys re-pointed: `Comparison.image1/2` → `statmaps_item`;
`Metaanalysis.maps` → `statmaps_item` (the use case enforces
`kind='statmap' and source is null`, which matches today's `StatisticMap` restriction).

Rejected schemas (see §11): keep multi-table inheritance, use one-to-one detail tables,
or a single table with a JSONB payload.

### API shape (D3)

The serializer derives the legacy strings from the composed entity instead of
`isinstance`:

| Entity | `image_type` (API) | datatables label (`views.py:1413`) |
|--------|--------------------|-------------------------------------|
| `StatMap`, `source is None` | `statistic_map` | `statistic map` |
| `StatMap`, `source` set | `NIDM results statistic map` | `nidm result statistic map` |
| `Atlas` | `atlas` | `atlas` |
| `NIDMBundle` | `NIDM Results` | `nidm results` |
| `OtherImage` | no branch today: `to_representation` reaches `serializer(...)` unbound and raises. Phase 0 records the current behaviour; the fix (e.g. `image`) is a separate, explicit API change | `image` |

The serializers currently use `exclude = [...]`, so their output is whatever fields
the model happens to have. Collapsing the tables would silently change keys
(`image_ptr`, `basecollectionitem_ptr`). Phase 0 replaces `exclude` with explicit
`fields` lists frozen from golden responses.

## 7. Evidence from the local database

Queries run against `local_data/db` (Postgres 14) on 2026-10-21; script in the
session scratchpad, reproduced in Appendix A.

| Check | Result | Consequence |
|-------|--------|-------------|
| Items by polymorphic type | 126, all `statisticmap` | no plain `image` rows locally (D4 is a rule with no local cases) |
| Orphans or multiple child rows | 0 | the `INSERT … SELECT` join is total for this data |
| Per-item guardian rows | 348 (+40 collection rows), all on content type `basecollectionitem` | matches `GUARDIAN_GET_CONTENT_TYPE` polymorphic setting |
| Per-item rows not explained by owner or contributor | **0** | D7 is safe on this data |
| Items missing the owner's per-item permission | 0 | dropping rows loses no access, grants none |
| Group object permissions | 0 | nothing to migrate |
| Taggit rows | 0 | the content-type remap is untested by data |
| Atlas, NIDM results, NIDM statmaps, comparisons, metaanalysis maps | 0 each | those paths are untested by data |
| `max(basecollectionitem.id)` | 174 | sequence start for the new tables |

The local database covers only `statisticmap`. The migration test (§9) must
create fixtures for every other kind, plus tags and comparisons, using the existing
test helpers (`apps/statmaps/tests/utils.py`, `test_nidm.py`, `api/tests/test_atlas.py`).
Re-run Appendix A on a production snapshot before the maintenance window.

### Mapper prototype (2026-10-21)

`prototype/collection_item_mapper/` (throwaway): composed entities (`domain.py`,
no Django imports), a declarative ORM↔entity mapper with a repository (`mapper.py`,
132 non-comment lines), and `roundtrip.py`. Run against `nv_proto`, a copy of the
dev database migrated to `0005` (the dev database itself is at `0002`).

| Check | Result |
|-------|--------|
| Every concrete column of the 5 ORM classes is mapped or persistence-derived (ptrs, `polymorphic_ctype`) | yes: 51/54, 41/44, 33/36, 32/34, 9/11; nothing unmapped, nothing invented |
| 126 real statistic maps: ORM → entity → ORM preserves every column; entity is stable on a second pass | yes |
| One fixture of each kind (statmap with Cognitive Atlas FKs and tags, NIDM bundle, NIDM statmap, atlas, other) built as entities, saved, reloaded polymorphically, compared | identical except `id`, `add_date`, `modify_date` (DB-assigned) |
| `legacy_image_type(entity)` equals today's serializer dispatch | yes, for all kinds (`other` → none, as today) |

What the prototype found:
- **Taggit stores the subclass content type** (`statisticmap`, `atlas`, `nidmresults`),
  so phase 4 must remap `statmaps_valuetaggeditem.content_type_id`.
- **The guardian `post_save` handlers still fire** when the repository bypasses the
  custom `save()` methods (16 per-item rows for the 5 fixtures), because they're
  connected to the model classes. Phase 1 must disconnect them along with the
  `save()` side effects.
- **Real data contains NaN** (`perc_voxels_outside` on item 91). It is preserved, but
  entity equality and any domain validation must treat NaN explicitly.
- **`Image.create` is dead and broken**: it writes `hdr_file` and `nifti_gz_file`,
  which aren't fields (`apps/statmaps/models.py:1190-1201`). Delete it in phase 1.
- `NIDMResultStatisticMap` and `StatisticMap` differ only by `Annotation` (modality,
  smoothing, statistic parameters, ignore-warning, Cognitive Atlas paradigm) versus
  `NIDMProvenance`. The invariant "exactly one of the two" holds for every row.

## 8. Migration sequence

Each phase is a separate PR and leaves `master` releasable.

| Phase | Work | Exit criterion |
|-------|------|----------------|
| 0. Safety net | Characterization tests: single and zip upload, folder upload, NIDM, surface, edit, move, delete, publish, contributors. Golden API responses for every endpoint and image kind. Explicit serializer `fields`. `import-linter` contracts (initially relaxed). | tests pass on current `master`; golden files committed |
| 1. Use cases on ORM | `application/services` operating on today's models; views, DRF, tasks and commands call them; side effects leave `save()` and signals; every `.save()` call site routed. | no `apply_async` and no file I/O in `models.py`; golden responses unchanged |
| 2. Ports | `TaskQueue`, `MapStore`, `SurfaceProjector`, `ThumbnailRenderer`, `PublicationLookup`, `OntologyGateway`, `Notifier`, `MetaAnalysisEngine` with in-memory fakes; use-case unit tests on fakes. | use-case tests run without Docker |
| 3. Domain entities | Composed `CollectionItem`, `NIDMBundle`, `Collection`; repositories and mappers over the **current polymorphic tables**; use cases switch to entities. | round-trip test: every fixture kind → entity → row is lossless |
| 4. Schema swap | New tables, data migration, FK re-pointing, guardian per-item delete, taggit content-type remap; the repository adapter switches tables. Run in a maintenance window (D5). | migration test passes on fixtures of every kind; Appendix A on the production snapshot shows 0 divergent permissions; golden responses unchanged |
| 5. Cleanup | Drop old tables, `polymorphic` from `INSTALLED_APPS` and requirements, polymorphic admin, `PolymorphicImageForm`, `ObjectOnlyPolymorphicPermissions`, `GUARDIAN_GET_CONTENT_TYPE`; tighten `import-linter`. | no `polymorphic` import remains |

Doing phases 1–3 before phase 4 means the 17 `instance_of` and the
`polymorphic_ctype` call sites are rewritten once, when they move into use cases and
repositories, and the schema swap touches only the persistence adapter.

## 9. Verification

- **Behaviour preservation:** golden API responses and characterization tests from
  phase 0 must pass unchanged after every phase (procedure: `preserving-behavior`).
- **Data migration:** forward-migrate a database seeded with one row of each kind
  (statmap, NIDM statmap, atlas, other, NIDM bundle), with tags, comparisons, a
  metaanalysis and a contributor. Compare every column, id, foreign key, tag and
  effective permission against the pre-migration state.
- **Access policy equivalence:** for every (user, item) pair in the seeded and local
  databases, `AccessPolicy` gives the same answer as guardian did before the swap.
- **Rehearsal:** run phase 4 against a restored production snapshot and time it to
  size the maintenance window.

## 10. Risks

| Risk | Mitigation |
|------|------------|
| Hidden reliance on `save()` side effects (admin, `image_metadata.py`, scripts, management commands) | phase 1 greps every `.save()` call site (66) and routes it; characterization tests |
| Serializer output drifts with model fields | explicit `fields` lists plus golden responses in phase 0 |
| Production data has shapes the local DB lacks (atlases, NIDM, tags, plain images, divergent permissions) | Appendix A on a snapshot before phase 4; fixtures for every kind |
| `MapStore` refactor is large (185 path uses; nibabel, nilearn and FreeSurfer need real paths) | `MapStore.local_path(ref)` context manager for tools that need a file; local adapter returns the real path |
| A three-person team keeps entities and ORM models in sync | mappers are tested by the lossless round-trip; entity fields are grouped into value objects, so one mapper per group |
| Long-running branch | each phase merges independently; no feature freeze needed except the phase 4 window |

## 11. Alternatives considered and dropped

- **Ports around external parts only, ORM models as entities.** Cheaper, and is
  phases 0–2 of this plan, but leaves the domain bound to Django (rejected by D1).
- **Service layer only, no ports (HackSoft styleguide).** Use cases would still need
  the filesystem, Celery and FreeSurfer in tests.
- **Full hexagon that mirrors the inheritance tree.** Mappers for a four-level class
  hierarchy on both sides; composition gives one entity with a payload union.
- **Keep multi-table inheritance without django-polymorphic.** Still five tables and
  manual downcasting; NIDM statmaps stay a separate type although they differ only
  by provenance.
- **Base table plus one-to-one detail tables.** Same mapping complexity as a single
  table, with joins on every read and no benefit at about 20 optional columns.
- **Single table with a JSONB payload.** `map_type`, `analysis_level` and the
  Cognitive Atlas foreign keys are filtered on (`utils.py:648`, datatables views)
  and would lose indexes and referential integrity.

## Appendix A — verification queries

```sql
-- items per polymorphic type
SELECT ct.model, count(*) FROM statmaps_basecollectionitem b
JOIN django_content_type ct ON ct.id = b.polymorphic_ctype_id GROUP BY 1;

-- taggit content types
SELECT ct.app_label || '.' || ct.model, count(*) FROM statmaps_valuetaggeditem t
JOIN django_content_type ct ON ct.id = t.content_type_id GROUP BY 1;

-- per-item permissions not explained by owner/contributor (must be 0)
SELECT count(*) FROM guardian_userobjectpermission p
JOIN django_content_type ct ON ct.id = p.content_type_id AND ct.model = 'basecollectionitem'
JOIN statmaps_basecollectionitem b ON b.id = p.object_pk::int
JOIN statmaps_collection c ON c.id = b.collection_id
WHERE p.user_id <> c.owner_id
  AND p.user_id NOT IN (SELECT user_id FROM statmaps_collection_contributors
                        WHERE collection_id = c.id);

-- items whose owner lacks the per-item permission (must be 0)
SELECT count(*) FROM statmaps_basecollectionitem b
JOIN statmaps_collection c ON c.id = b.collection_id
WHERE NOT EXISTS (
  SELECT 1 FROM guardian_userobjectpermission p
  JOIN django_content_type ct ON ct.id = p.content_type_id AND ct.model = 'basecollectionitem'
  WHERE p.object_pk = b.id::text AND p.user_id = c.owner_id);

-- group object permissions (must be 0, or migrated explicitly)
SELECT count(*) FROM guardian_groupobjectpermission;

-- sequence start for the new tables
SELECT max(id) FROM statmaps_basecollectionitem;
```
