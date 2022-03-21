def solve_community_identifier(request):
    # TODO: This is shitty
    if len(request.get_host().split(".")) < 3:
        return "riskofrain2"
    else:
        return request.get_host().split(".")[0]
