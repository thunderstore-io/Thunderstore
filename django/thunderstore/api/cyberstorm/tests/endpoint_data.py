post_payload_map = {
    "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/approve/": {
        "internal_notes": "This is an example internal note",
    },
    "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/reject/": {
        "rejection_reason": "This is an example rejection reason",
    },
    "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/update/": {
        "categories": ["test"],
    },
    "/api/cyberstorm/package/{namespace_id}/{package_name}/deprecate/": {
        "deprecate": True,
    },
    "/api/cyberstorm/package/{namespace_id}/{package_name}/rate/": {
        "target_state": "rated"
    },
    "/api/cyberstorm/team/create/": {
        "name": "TestTeam",
    },
    "/api/cyberstorm/team/{team_name}/member/add/": {
        "username": "TestUser",
        "role": "member",
    },
    "/api/cyberstorm/team/{team_name}/service-account/create/": {
        "nickname": "TestServiceAccount",
    },
}


patch_payload_map = {
    "/api/cyberstorm/team/{team_name}/update/": {
        "donation_link": "https://example.com/donate",
    }
}


GET_TEST_CASES = [
    {"path": "/api/cyberstorm/community/"},
    {"path": "/api/cyberstorm/community/{community_id}/"},
    {"path": "/api/cyberstorm/community/{community_id}/filters/"},
    {"path": "/api/cyberstorm/listing/{community_id}/"},
    {"path": "/api/cyberstorm/listing/{community_id}/{namespace_id}/"},
    {"path": "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/"},
    {
        "path": "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/dependants/"
    },
    {
        "path": "/api/cyberstorm/package/{community_id}/{namespace_id}/{package_name}/permissions/"
    },
    {"path": "/api/cyberstorm/package/{namespace_id}/{package_name}/latest/changelog/"},
    {"path": "/api/cyberstorm/package/{namespace_id}/{package_name}/latest/readme/"},
    {
        "path": "/api/cyberstorm/package/{namespace_id}/{package_name}/v/{version_number}/changelog/"
    },
    {
        "path": "/api/cyberstorm/package/{namespace_id}/{package_name}/v/{version_number}/readme/"
    },
    {"path": "/api/cyberstorm/package/{namespace_id}/{package_name}/versions/"},
    {"path": "/api/cyberstorm/team/{team_id}/"},
    {"path": "/api/cyberstorm/team/{team_id}/member/"},
    {"path": "/api/cyberstorm/team/{team_id}/service-account/"},
]


POST_TEST_CASES = [
    {
        "path": path,
        "payload": post_payload_map[path],
    }
    for path in post_payload_map.keys()
]


PATCH_TEST_CASES = [
    {
        "path": path,
        "payload": patch_payload_map[path],
    }
    for path in patch_payload_map.keys()
]


DELETE_TEST_CASES = [
    {"path": "/api/cyberstorm/team/{team_name}/disband/"},
    {"path": "/api/cyberstorm/team/{team_name}/service-account/delete/{uuid}/"},
]
