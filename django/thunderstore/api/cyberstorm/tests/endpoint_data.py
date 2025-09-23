ENDPOINTS = {
    "GET": [
        "/api/cyberstorm/community/",
        "/api/cyberstorm/community/{community_id}/",
        "/api/cyberstorm/community/{community_id}/filters/",
        "/api/cyberstorm/listing/{community_id}/",
        "/api/cyberstorm/listing/{community_id}/{namespace_id}/",
        "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/",
        "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/status/",
        "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/dependants/",
        "/api/cyberstorm/package/{community_id}/{namespace_id}/{package_name}/permissions/",
        "/api/cyberstorm/package/{namespace_id}/{package_name}/latest/changelog/",
        "/api/cyberstorm/package/{namespace_id}/{package_name}/latest/readme/",
        "/api/cyberstorm/package/{namespace_id}/{package_name}/v/{version_number}/",
        "/api/cyberstorm/package/{namespace_id}/{package_name}/v/{version_number}/changelog/",
        "/api/cyberstorm/package/{namespace_id}/{package_name}/v/{version_number}/readme/",
        "/api/cyberstorm/package/{namespace_id}/{package_name}/v/{version_number}/dependencies/",
        "/api/cyberstorm/package/{namespace_id}/{package_name}/versions/",
        "/api/cyberstorm/team/{team_id}/",
        "/api/cyberstorm/team/{team_id}/member/",
        "/api/cyberstorm/team/{team_id}/service-account/",
    ],
    "POST": {
        "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/approve/": {
            "internal_notes": "This is an example internal note",
        },
        "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/reject/": {
            "rejection_reason": "This is an example rejection reason",
        },
        "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/update/": {
            "categories": ["test"],
        },
        "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/report/": {
            "reason": "Spam",
        },
        "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/unlist/": {},
        "/api/cyberstorm/package/{namespace_id}/{package_name}/deprecate/": {
            "deprecate": True,
        },
        "/api/cyberstorm/package/{namespace_id}/{package_name}/rate/": {
            "target_state": "rated",
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
    },
    "PATCH": {
        "/api/cyberstorm/team/{team_name}/update/": {
            "donation_link": "https://example.com/donate",
        },
    },
    "DELETE": [
        "/api/cyberstorm/team/{team_name}/disband/",
        "/api/cyberstorm/team/{team_name}/member/{username}/remove/",
        "/api/cyberstorm/team/{team_name}/service-account/delete/{uuid}/",
        "/api/cyberstorm/user/delete/",
        "/api/cyberstorm/user/linked-account/{provider}/disconnect/",
    ],
}


GET_TEST_CASES = [{"path": path} for path in ENDPOINTS["GET"]]


POST_TEST_CASES = [
    {"path": path, "payload": payload} for path, payload in ENDPOINTS["POST"].items()
]


PATCH_TEST_CASES = [
    {"path": path, "payload": payload} for path, payload in ENDPOINTS["PATCH"].items()
]


DELETE_TEST_CASES = [{"path": path} for path in ENDPOINTS["DELETE"]]
