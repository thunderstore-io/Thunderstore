# Feature Parity Document: Legacy vs New App

**Legacy App:** [thunderstore.io](https://thunderstore.io)
**New App:** [new.thunderstore.io](https://new.thunderstore.io)
**Local API docs:** [DOCS](http://localhost.thunderstore/api/docs)
---

## Status Legend

- ✅ Complete
- ⚠️ Partial
- ❌ Missing

---

## Feature Comparison

### Complete

#### Community

| Feature | Legacy App | New App | Status | Notes |
|---------|------------|---------|--------|-------|
|Get community list| ✅ | ✅ | Complete | GET /community/ |
|Get community| ✅ | ✅ | Complete | GET /community/{community_id}/ |
|Filter community| ✅ | ✅ | Complete | GET /community/{community_id}/filters/ |

#### Package listing

| Feature | Legacy App | New App | Status | Notes |
|---------|------------|---------|--------|-------|
|Get listing list for community| ✅ | ✅ | Complete | GET /listing/{community_id}/ |
|Get listing with community and namespace| ✅ | ✅ | Complete | GET /listing/{community_id}/{namespace_id}/ |
|Get listing with community, namespace and package name| ✅ | ✅ | Complete | GET /listing/{community_id}/{namespace_id}/{package_name}/ |
|Approve package listing| ✅ | ✅ | Complete | POST /listing/{community_id}/{namespace_id}/{package_name}/approve/ |
|Get packages depending on this package| ✅ | ✅ | Complete | GET /listing/{community_id}/{namespace_id}/{package_name}/dependants/ |
|Reject a package listing| ✅ | ✅ | Complete | POST /listing/{community_id}/{namespace_id}/{package_name}/reject/ |
|Update a package listing| ✅ | ✅ | Complete | POST /listing/{community_id}/{namespace_id}/{package_name}/update/ |

#### Package

| Feature | Legacy App | New App | Status | Notes |
|---------|------------|---------|--------|-------|
|Get the permissions for a package| ✅ | ✅ | Complete | GET /package/{community_id}/{namespace_id}/{package_name}/permissions/ |
|Deprecate a package| ✅ | ✅ | Complete | POST /package/{namespace_id}/{package_name}/deprecate/ |
|Get package changelog as html| ✅ | ✅ | Complete | GET /package/{namespace_id}/{package_name}/latest/changelog/ |
|Get package readme as html| ✅ | ✅ | Complete | GET /package/{namespace_id}/{package_name}/latest/readme/ |
|Rate a package| ✅ | ✅ | Complete | POST /package/{namespace_id}/{package_name}/rate/ |
|Get package version changelog| ✅ | ✅ | Complete | GET /package/{namespace_id}/{package_name}/v/{version_number}/changelog/ |
|Get package version readme| ✅ | ✅ | Complete | GET /package/{namespace_id}/{package_name}/v/{version_number}/readme/ |
|Get all versions for package| ✅ | ✅ | Complete | GET /package/{namespace_id}/{package_name}/versions/ |

#### Team

| Feature | Legacy App | New App | Status | Notes |
|---------|------------|---------|--------|-------|
|Create a new team| ✅ | ✅ | Complete | POST /team/create/ |
|Get team info| ✅ | ✅ | Complete | GET /team/{team_id}/ |
|Get list of team members| ✅ | ✅ | Complete | GET /team/{team_id}/member/ |
|Get service accounts for team| ✅ | ✅ | Complete | GET /team/{team_id}/service-account/ |
|Disband a team| ✅ | ✅ | Complete | DELETE /team/{team_name}/disband/ |
|Add a new team member to a team| ✅ | ✅ | Complete | POST /team/{team_name}/member/add/ |
|Update team details| ✅ | ✅ | Complete | PATCH /team/{team_name}/update/ |


### Partial

| Feature | Legacy App | New App | Status | Notes |
|---------|------------|---------|--------|-------|
| Get Package Listing status info | ✅ | ⚠️ | Partial | In review [PR](https://github.com/thunderstore-io/Thunderstore/pull/1179) |
| Unlist Package | ✅ | ⚠️ | Partial | In review [PR](https://github.com/thunderstore-io/Thunderstore/pull/1178) |
| Fetch package source | ✅ | ⚠️ | Partial | In review [PR](https://github.com/thunderstore-io/Thunderstore/pull/1094) |
| Create service account | ✅ | ⚠️ | Partial | In review [PR](https://github.com/thunderstore-io/Thunderstore/pull/1098) |
| Delete service account | ✅ | ⚠️ | Partial | In review [PR](https://github.com/thunderstore-io/Thunderstore/pull/1098) |
| Delete user | ✅ | ⚠️ | Partial | In review [PR](https://github.com/thunderstore-io/Thunderstore/pull/1114) |
| Delete social auth account | ✅ | ⚠️ | Partial | In review [PR](https://github.com/thunderstore-io/Thunderstore/pull/1114) |
| Update team member info | ✅ | ⚠️ | Partial | In review [PR](https://github.com/thunderstore-io/Thunderstore/pull/1117) |
| Delete team member | ✅ | ⚠️ | Partial | In review [PR](https://github.com/thunderstore-io/Thunderstore/pull/1118) |


### Missing

| Feature | Legacy App | New App | Status | Notes |
|---------|------------|---------|--------|-------|
| Leave team | ✅ | ❌ | TODO | No API endpoint |
| Report package | ✅ | ❌ | TODO | No Cyberstorm API endpoint - exists in experimental API |
| Upload new package | ✅ | ❌ | TODO? | How should this be handled? |


---

## Notes & Recommendations

- Prioritize high-impact missing features.
- Identify API gaps that block feature parity.
- Suggest roadmap or implementation order if possible.

