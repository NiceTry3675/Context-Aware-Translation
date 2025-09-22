### Structural problems

- Domain boundaries and coupling
  - **Direct coupling to `User`**: `Post`/`Comment` models and Pydantic schemas reference `User` models/schemas, and `User` has backrefs (`posts`, `comments`), tightly coupling domains (`backend/domains/community/models.py`, `backend/domains/user/models.py`, `backend/domains/community/schemas.py`).
  - **Announcements live in multiple domains**: `Announcement` model is in community, but creation/listing/streaming are handled in user and admin domains, plus a community repository exists but isn’t used consistently (`backend/domains/community/models.py`, `backend/domains/user/service.py`, `backend/domains/admin/routes.py`, `backend/domains/community/repository.py`).
- Authorization duplication and mismatch
  - **Duplicated permission logic**: Policy layer (`backend/domains/community/policy.py`) and repositories (`can_user_view/can_user_edit`) both implement access rules; services call repositories instead of policies, creating multiple sources of truth.
  - **Policy-model mismatch**: Policy checks `post.is_locked` and supports `Action.LOCK`, but `Post` lacks `is_locked` and there’s no lock/unlock endpoint.
  - **Two RBAC styles**: Community uses its own `Policy`; admin uses `Permission` enforcement; roles are compared as raw strings across code.
- Persistence and transaction boundaries
  - **Unit of Work misuse/inconsistency**: UoW is synchronous, but user service uses `async with`; community services mix `uow.session` and `self.session`, and pass `lambda: self.session` (re-using the same session instead of a factory), muddying transactional boundaries.
  - **Repository Protocol misuse**: `PostCategoryRepositoryProtocol` is declared as a `Protocol` but contains concrete logic (calling `super().__init__`), then duplicated again in `SqlAlchemyPostCategoryRepository`, which is error-prone and confusing.
- API and data-leak risks
  - **Incorrect totals for paginated lists**: `list_posts` includes private posts in the DB query and only filters in Python, so `X-Total-Count` can reveal private content counts to unauthorized users.
  - **Search/list privacy**: Similar include/exclude-private logic is scattered and inconsistent.
- Schema design
  - **Community schemas depend on user schemas**: `Post`, `PostList`, and `Comment` embed `User` instead of a minimal author view model, increasing coupling and payload size.
  - **Announcement schema defined in user domain** while model is in community domain.
- Dead code / incompleteness
  - **Unimplemented features referenced**: `Action.LOCK` without `is_locked` or endpoints; category admin policy without category management endpoints.
- Minor correctness/quality issues
  - **Type hint causing runtime name lookup**: `CategoryService` uses `PostRepository` in an annotation without importing it.
  - **Unused variables / noise**: e.g., `include_private` variable computed but unused in `PostService.list_posts`.

### Refactoring plan

- Phase 0: Quick fixes (low-risk, immediate)
  - Import or remove the `PostRepository` annotation in `CategoryService`; remove unused variables; standardize on one session reference inside services (`uow.session`).
  - Route totals: ensure `X-Total-Count` reflects only items visible to the caller.

- Phase 1: Clarify domain ownership for Announcements and consolidate
  - Keep `Announcement` in community domain. Move all announcement creation/listing/streaming logic into a `community` service/router and delete duplicates from `user`/`admin`.
  - Use `SqlAlchemyAnnouncementRepository` everywhere; expose `GET /community/announcements`, `POST /community/announcements`, `PUT/DELETE` (admin-only). Adjust `backend/routes.py` to route via community.

- Phase 2: Unify authorization
  - Make the community `Policy` the single source of truth. Remove `can_user_view`/`can_user_edit` from repositories; services should always call `check_policy`/`enforce_policy`.
  - Replace raw `role == "admin"` checks with a small permission abstraction or centralized role helper used by Policy.
  - Either implement locking fully or remove it:
    - Implement: add `Post.is_locked` (+ migration), policy stays as-is, add `POST /community/posts/{id}/lock|unlock`.
    - Or defer: remove `Action.LOCK` and related checks until needed.

- Phase 3: Transactions and Unit of Work
  - Make UoW consistent:
    - Provide an async-capable UoW (add `__aenter__/__aexit__`) or convert services to sync methods called from async endpoints.
    - Pass a proper session factory (e.g., `sessionmaker`) to UoW so each use has a clear transaction boundary.
    - Within services, use `uow.session` exclusively for reads/writes/flushes.
  - Ensure events are collected and (later) dispatched via a single event dispatcher.

- Phase 4: Repository layer cleanup
  - Replace `PostCategoryRepositoryProtocol` with a clean ABC or use the existing `SqlAlchemyRepository` base only. Remove duplicate/invalid implementations and keep one `PostCategoryRepository`.
  - Keep repositories persistence-focused; remove authorization logic.

- Phase 5: Model and schema decoupling
  - Keep FK to `users.id` in DB, but remove backrefs from `backend/domains/user/models.py` to posts/comments to reduce two-way coupling.
  - Introduce a minimal `AuthorSummary` schema in community (e.g., `id`, `name`) and use that in `Post`, `PostList`, `Comment`.
  - Optionally introduce a shared `UserContext` interface to pass minimal user info into policies/services.

- Phase 6: API completeness and consistency
  - Add lock/unlock endpoints if locking retained; add category admin endpoints if category policy remains.
  - Standardize response models to the decoupled schemas and ensure OpenAPI matches.

- Phase 7: Data privacy correctness
  - Push visibility filtering into queries (using a specification or query builder that takes the caller) so both items and counts are consistent and non-leaky.
  - Add tests for visibility rules (author, admin, unauthenticated) for list/search/details.

- Phase 8: Tests and migration
  - DB migration for `posts.is_locked` if implemented.
  - Unit tests for policies, services, and repositories; endpoint tests for all community routes.
  - Remove dead code and update docs (`DOMAIN_BOUNDARIES.md`).

### Expected outcomes

- Clear domain ownership (community fully owns announcements and board).
- Single authorization model with no duplicated logic.
- Correct transaction boundaries and easier maintenance via clean repositories.
- Reduced coupling to user domain via minimal author views.
- Privacy-safe pagination/search and a stable surface for future features (locking, moderation).

In short: centralize announcements in community, unify and fix policy enforcement, clean the repository/UoW layers, decouple schemas from `User`, and close the policy–model gap (locking) with migrations and endpoints.

I’ve finished reviewing and outlined the issues and a phased refactor plan.